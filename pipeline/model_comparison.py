"""Walk-forward model comparison (logistic regression, random forest, LightGBM, MLP).

Everything is evaluated by season, never random splits:
  test season T  <-  train on a window of seasons BEFORE T, never T itself.

Inside every training window the most recent season is held out as an
"inner validation" season. Hyperparameters, early-stopping rounds and
calibration are chosen using that season only. The test season is only ever
scored, never used to tune anything.

Per (test season, recency window, sample weighting) the script:
  1. fits every config of every model family on the window minus its last season,
     scores it on the inner validation season, and picks each family's best
     config by validation log loss ("selected");
  2. refits each config on the whole window (train + validation season) and
     scores it on the test season ("candidate" rows, descriptive only);
  3. builds calibrated versions (Platt / isotonic fitted on the validation season
     using the model trained WITHOUT that season) and equal-weight ensembles of
     the selected configs;
  4. also records two baselines: always-home (constant home-win rate) and a
     default logistic regression.

Features are built the same way for training and test rows (rolling 7/30-day
pre-game averages, point-in-time player values, per-game inactives, back-to-back
flags) -- see build_season below.

Usage:
    export NBA_DB_PATH=~/nba-data/nba_data_full.db
    python3 pipeline/model_comparison.py                 # run everything
    python3 pipeline/model_comparison.py --smoke         # one fold, one combo, quick check
    python3 pipeline/model_comparison.py --summarize     # (re)write results/SUMMARY.md from the CSVs
"""

import argparse
import copy
import os
import pickle
import sqlite3
import sys
import time
import warnings
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / 'backend'))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import database
from data import (
    get_game_window_features, GAME_WINDOWS, NotEnoughHistory,
    get_injury_value, get_injury_advanced, scrape_back_to_back,
)
from utils import season_label_for_date

RESULTS_DIR = REPO_ROOT / 'results'
FEATURES_CACHE = RESULTS_DIR / 'features_cache.pkl'
# Bump whenever build_season's output changes, so a stale cache can never be reused.
FEATURE_VERSION = 'game-windows-v2'
FOLDS_CSV = RESULTS_DIR / 'folds.csv'
CALIBRATION_CSV = RESULTS_DIR / 'calibration.csv'
DROPS_CSV = RESULTS_DIR / 'feature_drops.csv'
COVERAGE_CSV = RESULTS_DIR / 'data_coverage.csv'
SUMMARY_MD = RESULTS_DIR / 'SUMMARY.md'

SEED = 42

# Inactive-player lists (game_injuries) only exist from 2005-06 on, so earlier
# seasons would have no injury signal at all. "All prior seasons" starts here.
FIRST_SEASON = '2005-06'
FIRST_TEST_SEASON = '2016-17'
LAST_SEASON = '2025-26'  # latest complete season in the DB

FEATURE_COLUMNS = [
    'Home ORtg', 'Away ORtg', 'Home eFG%', 'Away eFG%',
    'Home TOV%', 'Away TOV%', 'Home ORB%', 'Away ORB%',
    'Home Injury Value', 'Away Injury Value',
    'Home Injury Advanced', 'Away Injury Advanced',
    'Home B2B', 'Away B2B',
]

# Recency experiments: how many prior seasons to train on (None = all), and
# exponential-decay sample weights (half-life in seasons; None = equal weights).
WINDOWS = {'last3': 3, 'last5': 5, 'last8': 8, 'all': None}
WEIGHTINGS = {'none': None, 'hl2': 2, 'hl5': 5}

TIE_MARGIN = 0.002  # log-loss differences below this are treated as ties

# Final per-model setup: how much history each family gets, no recency weighting.
#  - mlp / lgbm / lr: all prior seasons (more data helped or tied for every one of these in the grid)
#  - rf: last 5 seasons (diminishing returns beyond that)
PER_MODEL_WINDOWS = {'lr': 'all', 'lgbm': 'all', 'mlp': 'all', 'rf': 'last5'}
PER_MODEL_CSV = RESULTS_DIR / 'per_model_final.csv'

# Ablation: DROP_INJURIES=1 removes the four injury columns (same features otherwise)
# and writes to a separate CSV so the main results are not overwritten.
DROP_INJURIES = os.environ.get('DROP_INJURIES') == '1'
if DROP_INJURIES:
    FEATURE_COLUMNS = [c for c in FEATURE_COLUMNS if 'Injury' not in c]
    FEATURES_CACHE = RESULTS_DIR / 'features_cache_no_injuries.pkl'
    PER_MODEL_CSV = RESULTS_DIR / 'per_model_no_injuries.csv'
if os.environ.get('PER_MODEL_OUT'):  # write a per-model run somewhere else instead of overwriting results
    PER_MODEL_CSV = Path(os.environ['PER_MODEL_OUT'])


# ---------------------------------------------------------------- features

def games_by_season():
    conn = sqlite3.connect(database.DB_PATH)
    rows = conn.execute('SELECT id, date, home_team, away_team, home_win FROM games ORDER BY date').fetchall()
    conn.close()
    seasons = defaultdict(list)
    for row in rows:
        seasons[season_label_for_date(row[1])].append(row)
    return seasons


def build_season(season, games):
    """Feature rows for one season. Every feature uses only days BEFORE the game date.

    A game is dropped if feature building raises (this is the try/except we
    want to count). Rows where a team had no games at all in the lookback
    (the data layer then silently returns 0) are counted as zero_filled.
    """
    rows, dropped, short_history = [], 0, 0
    for game_id, date, home, away, home_win in games:
        try:
            factors = get_game_window_features(date, home, away)
            home_b2b, away_b2b = scrape_back_to_back(date, home, away)
            row = {
                'season': season, 'game_id': game_id, 'date': date,
                **factors,
                'Home B2B': home_b2b, 'Away B2B': away_b2b,
                'Home Win': home_win,
            }
            if not DROP_INJURIES:
                home_inj = database.get_game_injuries(game_id, home)
                away_inj = database.get_game_injuries(game_id, away)
                row.update({
                    'Home Injury Value': get_injury_value(home_inj, home, date),
                    'Away Injury Value': get_injury_value(away_inj, away, date),
                    'Home Injury Advanced': get_injury_advanced(home_inj, home, date),
                    'Away Injury Advanced': get_injury_advanced(away_inj, away, date),
                })
        except NotEnoughHistory:
            short_history += 1  # expected: a team's first few games in the data have nothing to average
            continue
        except Exception:
            dropped += 1  # unexpected: the caller should treat a high count as a data problem
            continue
        rows.append(row)
    df = pd.DataFrame(rows)
    zero_filled = 0  # kept for the drops table; games without enough history are dropped, never zero-filled
    return season, df, {'season': season, 'games': len(games), 'rows': len(df),
                        'dropped': dropped, 'short_history': short_history, 'zero_filled': zero_filled}


def _db_signature():
    st = os.stat(database.DB_PATH)
    return (database.DB_PATH, st.st_size, int(st.st_mtime))


def load_features(workers, last_season=LAST_SEASON):
    """Feature rows for every season from FIRST_SEASON through last_season (cached per DB file)."""
    sig = _db_signature()
    if FEATURES_CACHE.exists():
        with open(FEATURES_CACHE, 'rb') as f:
            cached = pickle.load(f)
        if cached.get('sig') == sig and cached.get('last_season') == last_season and cached.get('windows') == GAME_WINDOWS and cached.get('version') == FEATURE_VERSION:
            print(f'Loaded cached features from {FEATURES_CACHE}')
            return cached['df'], cached['drops']
    seasons = games_by_season()
    wanted = [s for s in sorted(seasons) if FIRST_SEASON <= s <= last_season]
    print(f'Building features for {len(wanted)} seasons ({wanted[0]}..{wanted[-1]}) with {workers} workers...')
    t0 = time.time()
    results = Parallel(n_jobs=workers)(delayed(build_season)(s, seasons[s]) for s in wanted)
    df = pd.concat([r[1] for r in results], ignore_index=True)
    drops = pd.DataFrame([r[2] for r in results])
    print(f'Built {len(df)} rows in {(time.time() - t0) / 60:.1f} min')
    print(drops.to_string(index=False))
    with open(FEATURES_CACHE, 'wb') as f:
        pickle.dump({'sig': sig, 'last_season': last_season, 'windows': GAME_WINDOWS, 'version': FEATURE_VERSION, 'df': df, 'drops': drops}, f)
    return df, drops


def write_coverage():
    """Inactive-list / box-score coverage per season, straight from the DB."""
    conn = sqlite3.connect(database.DB_PATH)
    q = '''
        SELECT g.id, g.date,
               EXISTS(SELECT 1 FROM team_stats t WHERE t.game_id = g.id) AS has_team_stats,
               EXISTS(SELECT 1 FROM player_game_stats p WHERE p.game_id = g.id) AS has_player_stats,
               EXISTS(SELECT 1 FROM game_injuries i WHERE i.game_id = g.id) AS has_inactives
        FROM games g
    '''
    df = pd.read_sql_query(q, conn)
    conn.close()
    df['season'] = df['date'].map(season_label_for_date)
    cov = df.groupby('season')[['has_team_stats', 'has_player_stats', 'has_inactives']].sum()
    cov.insert(0, 'games', df.groupby('season').size())
    cov = cov[(cov.index >= FIRST_SEASON) & (cov.index <= LAST_SEASON)]
    cov.to_csv(COVERAGE_CSV)


# ---------------------------------------------------------------- metrics

def metrics(y, p):
    p = np.clip(np.asarray(p, dtype=float), 1e-6, 1 - 1e-6)
    y = np.asarray(y)
    return {
        'logloss': float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))),
        'brier': float(np.mean((p - y) ** 2)),
        'acc': float(np.mean((p >= 0.5) == y)),
    }


def calibration_buckets(y, p, n_buckets=10):
    y, p = np.asarray(y), np.asarray(p)
    edges = np.linspace(0, 1, n_buckets + 1)
    out = []
    for i in range(n_buckets):
        lo, hi = edges[i], edges[i + 1]
        mask = (p >= lo) & ((p <= hi) if i == n_buckets - 1 else (p < hi))
        if mask.sum():
            out.append((f'{lo:.1f}-{hi:.1f}', int(mask.sum()), float(p[mask].mean()), float(y[mask].mean())))
    return out


# ---------------------------------------------------------------- models
# Each runner fits on the train part, scores validation + test, then refits on
# the full window and scores test. Returns the three probability arrays.

def recency_weights(season_idx, last_idx, half_life):
    """Weight 1.0 for the newest season in the fit set, halving every `half_life` seasons back."""
    if half_life is None:
        return None
    return 0.5 ** ((last_idx - season_idx) / half_life)


def _logreg(C=None, standardize=True):
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    if C is None:  # default settings (only max_iter raised so it converges)
        return make_pipeline(LogisticRegression(max_iter=1000)), 'logisticregression__sample_weight'
    return make_pipeline(StandardScaler(), LogisticRegression(C=C, max_iter=1000)), 'logisticregression__sample_weight'


def run_sklearn(make, tp, val, full, test):
    """Generic runner for models whose hyperparameters are fixed (no early stopping)."""
    (X_tp, y_tp, w_tp), (X_val, _), (X_full, y_full, w_full), X_test = tp, val, full, test
    model, wkey = make()
    model.fit(X_tp, y_tp, **({wkey: w_tp} if w_tp is not None else {}))
    p_val = model.predict_proba(X_val)[:, 1]
    p_test_tp = model.predict_proba(X_test)[:, 1]
    model, wkey = make()
    model.fit(X_full, y_full, **({wkey: w_full} if w_full is not None else {}))
    return p_val, p_test_tp, model.predict_proba(X_test)[:, 1], ''


def run_rf(params):
    from sklearn.ensemble import RandomForestClassifier

    def make():
        return RandomForestClassifier(random_state=SEED, n_jobs=1, **params), 'sample_weight'

    return lambda tp, val, full, test: run_sklearn(make, tp, val, full, test)


def run_lgbm(depth, lr, min_child):
    import lightgbm as lgb

    def build(n):
        return lgb.LGBMClassifier(
            n_estimators=n, learning_rate=lr, max_depth=depth, num_leaves=2 ** depth,
            min_child_samples=min_child, subsample=0.8, subsample_freq=1, colsample_bytree=0.8,
            reg_lambda=1.0, random_state=SEED, n_jobs=1, verbose=-1)

    def run(tp, val, full, test):
        (X_tp, y_tp, w_tp), (X_val, y_val), (X_full, y_full, w_full), X_test = tp, val, full, test
        m = build(2000)
        # early stopping watches the inner validation season only
        m.fit(X_tp, y_tp, sample_weight=w_tp, eval_set=[(X_val, y_val)], eval_metric='binary_logloss',
              callbacks=[lgb.early_stopping(100, verbose=False)])
        best = int(m.best_iteration_ or 1)
        p_val = m.predict_proba(X_val)[:, 1]
        p_test_tp = m.predict_proba(X_test)[:, 1]
        m2 = build(best)
        m2.fit(X_full, y_full, sample_weight=w_full)
        return p_val, p_test_tp, m2.predict_proba(X_test)[:, 1], f'best_iter={best}'

    return run


def run_mlp(hidden, alpha, max_epochs=150, patience=12):
    from sklearn.exceptions import ConvergenceWarning
    from sklearn.neural_network import MLPClassifier
    from sklearn.preprocessing import StandardScaler

    def build():
        # max_iter=1 + warm_start: each .fit() call is one more epoch, so we can
        # stop on the validation season's log loss.
        return MLPClassifier(hidden_layer_sizes=hidden, alpha=alpha, solver='adam', learning_rate_init=1e-3,
                             batch_size=256, max_iter=1, warm_start=True, random_state=SEED)

    def run(tp, val, full, test):
        (X_tp, y_tp, w_tp), (X_val, y_val), (X_full, y_full, w_full), X_test = tp, val, full, test
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', ConvergenceWarning)
            scaler = StandardScaler().fit(X_tp)
            m = build()
            best_loss, best_ep, snap = np.inf, 0, None
            for ep in range(1, max_epochs + 1):
                m.fit(scaler.transform(X_tp), y_tp, sample_weight=w_tp)
                loss = metrics(y_val, m.predict_proba(scaler.transform(X_val))[:, 1])['logloss']
                if loss < best_loss - 1e-5:
                    best_loss, best_ep = loss, ep
                    snap = (copy.deepcopy(m.coefs_), copy.deepcopy(m.intercepts_))
                elif ep - best_ep >= patience:
                    break
            m.coefs_, m.intercepts_ = snap
            p_val = m.predict_proba(scaler.transform(X_val))[:, 1]
            p_test_tp = m.predict_proba(scaler.transform(X_test))[:, 1]

            scaler2 = StandardScaler().fit(X_full)
            m2 = build()
            for _ in range(best_ep):
                m2.fit(scaler2.transform(X_full), y_full, sample_weight=w_full)
            p_test_full = m2.predict_proba(scaler2.transform(X_test))[:, 1]
        return p_val, p_test_tp, p_test_full, f'best_epochs={best_ep}'

    return run


def model_zoo():
    """{family: {config_name: runner}}."""
    return {
        'lr': {
            'std_C0.01': lambda *a: run_sklearn(lambda: _logreg(0.01), *a),
            'std_C0.1': lambda *a: run_sklearn(lambda: _logreg(0.1), *a),
            'std_C1': lambda *a: run_sklearn(lambda: _logreg(1.0), *a),
            'plain_default': lambda *a: run_sklearn(lambda: _logreg(None), *a),
        },
        'rf': {
            'current_n100': run_rf(dict(n_estimators=100)),
            'depth6_leaf50': run_rf(dict(n_estimators=300, max_depth=6, min_samples_leaf=50)),
            'depth4_leaf100': run_rf(dict(n_estimators=300, max_depth=4, min_samples_leaf=100)),
        },
        'lgbm': {
            'd3_lr0.03_mcs50': run_lgbm(3, 0.03, 50),
            'd4_lr0.03_mcs50': run_lgbm(4, 0.03, 50),
            'd3_lr0.03_mcs100': run_lgbm(3, 0.03, 100),
            'd4_lr0.03_mcs100': run_lgbm(4, 0.03, 100),
        },
        'mlp': {
            'h16_a1e-2': run_mlp((16,), 1e-2),
            'h32x16_a1e-2': run_mlp((32, 16), 1e-2),
            'h64_a1e-1': run_mlp((64,), 1e-1),
            'h64x32_a1e-1': run_mlp((64, 32), 1e-1),
        },
    }


# ---------------------------------------------------------------- one task

def calibrate(p_val, y_val, p_test_tp, kind):
    from sklearn.isotonic import IsotonicRegression
    from sklearn.linear_model import LogisticRegression
    if kind == 'platt':
        logit = lambda p: np.log(np.clip(p, 1e-6, 1 - 1e-6) / (1 - np.clip(p, 1e-6, 1 - 1e-6))).reshape(-1, 1)
        cal = LogisticRegression(C=1e6, max_iter=1000).fit(logit(p_val), y_val)
        return cal.predict_proba(logit(p_test_tp))[:, 1]
    iso = IsotonicRegression(out_of_bounds='clip', y_min=0.001, y_max=0.999).fit(p_val, y_val)
    return iso.predict(p_test_tp)


def run_task(df, test_season, window_name, weight_name, families=None, return_probs=False):
    """One (test season, recency window, weighting) cell. Returns (result rows, calibration rows)."""
    all_seasons = sorted(df['season'].unique())
    t_idx = all_seasons.index(test_season)
    prior = all_seasons[:t_idx]
    n = WINDOWS[window_name]
    window = prior[-n:] if n else prior
    train_seasons, val_season = window[:-1], window[-1]
    half_life = WEIGHTINGS[weight_name]

    def split(seasons_):
        part = df[df['season'].isin(seasons_)]
        idx = part['season'].map({s: all_seasons.index(s) for s in seasons_}).to_numpy()
        return part[FEATURE_COLUMNS].to_numpy(float), part['Home Win'].to_numpy(int), idx

    X_tp, y_tp, i_tp = split(train_seasons)
    X_val, y_val, _ = split([val_season])
    X_full, y_full, i_full = split(window)
    test = df[df['season'] == test_season]
    X_test, y_test = test[FEATURE_COLUMNS].to_numpy(float), test['Home Win'].to_numpy(int)

    w_tp = recency_weights(i_tp, i_tp.max(), half_life)
    w_full = recency_weights(i_full, i_full.max(), half_life)
    tp, val, full = (X_tp, y_tp, w_tp), (X_val, y_val), (X_full, y_full, w_full)

    base = dict(test_season=test_season, window=window_name, weighting=weight_name, n_test=len(y_test))
    rows, cal_rows = [], []

    def add(role, family, config, p, n_fit, val_loss=np.nan, extra=''):
        rows.append({**base, 'role': role, 'family': family, 'config': config, 'n_fit': n_fit,
                     'val_logloss': val_loss, 'extra': extra, **metrics(y_test, p)})
        if role != 'candidate':
            for bucket, cnt, avg_p, actual in calibration_buckets(y_test, p):
                cal_rows.append({**base, 'role': role, 'family': family, 'config': config,
                                 'bucket': bucket, 'n': cnt, 'avg_pred': avg_p, 'actual': actual})

    # Baselines. Always-home predicts the window's home-win rate with probability, and "home" as the pick.
    add('baseline_home', 'home', 'const', np.full(len(y_test), y_full.mean()), len(y_full))
    zoo = model_zoo()
    sel_full = {}
    for family, configs in zoo.items():
        if families and family not in families:
            continue
        best = None
        for name, runner in configs.items():
            p_val, p_test_tp, p_test_full, extra = runner(tp, val, full, X_test)
            val_loss = metrics(y_val, p_val)['logloss']
            add('candidate', family, name, p_test_full, len(y_full), val_loss, extra)
            if name == 'plain_default':
                add('baseline_lr', 'lr', 'plain_default', p_test_full, len(y_full), val_loss)
                if family == 'lr':
                    continue  # the default LR is the baseline, not a tuning candidate
            if best is None or val_loss < best[0]:
                best = (val_loss, name, p_val, p_test_tp, p_test_full, extra)
        val_loss, name, p_val, p_test_tp, p_test_full, extra = best
        add('selected', family, name, p_test_full, len(y_full), val_loss, extra)
        sel_full[family] = p_test_full
        for kind in ('platt', 'isotonic'):
            add(f'calibrated_{kind}', family, name, calibrate(p_val, y_val, p_test_tp, kind),
                len(y_tp), val_loss, 'base fit without validation season')

    if all(f in sel_full for f in ('lr', 'lgbm')):
        add('ensemble', 'ensemble', 'lr+lgbm', (sel_full['lr'] + sel_full['lgbm']) / 2, len(y_full))
    if all(f in sel_full for f in ('lr', 'lgbm', 'mlp')):
        add('ensemble', 'ensemble', 'lr+lgbm+mlp',
            (sel_full['lr'] + sel_full['lgbm'] + sel_full['mlp']) / 3, len(y_full))
    if return_probs:
        return rows, cal_rows, sel_full, y_test
    return rows, cal_rows


def _append(path, rows):
    pd.DataFrame(rows).to_csv(path, mode='a', header=not path.exists(), index=False)


def run_all(df, workers, smoke=False):
    all_seasons = sorted(df['season'].unique())
    test_seasons = [s for s in all_seasons if s >= FIRST_TEST_SEASON]
    combos = [(t, w, wt) for t in test_seasons for w in WINDOWS for wt in WEIGHTINGS]
    if smoke:
        combos = [(test_seasons[0], 'last5', 'hl2')]
    done = set()
    if FOLDS_CSV.exists() and not smoke:
        prev = pd.read_csv(FOLDS_CSV, usecols=['test_season', 'window', 'weighting']).drop_duplicates()
        done = set(map(tuple, prev.to_numpy()))
    todo = [c for c in combos if c not in done]
    print(f'{len(combos)} cells, {len(done)} already on disk, {len(todo)} to run ({workers} workers)')

    out_folds, out_cal = (RESULTS_DIR / 'smoke_folds.csv', RESULTS_DIR / 'smoke_calibration.csv') if smoke \
        else (FOLDS_CSV, CALIBRATION_CSV)
    t0 = time.time()
    gen = Parallel(n_jobs=workers, return_as='generator_unordered')(
        delayed(run_task)(df, *c) for c in todo)
    for k, (rows, cal_rows) in enumerate(gen, 1):
        _append(out_folds, rows)
        _append(out_cal, cal_rows)
        r = rows[0]
        print(f'[{k}/{len(todo)}] {r["test_season"]} {r["window"]}/{r["weighting"]} saved '
              f'({(time.time() - t0) / 60:.1f} min elapsed)', flush=True)


# ---------------------------------------------------------------- per-model final

def run_per_model_season(df, test_season):
    """Each family on its own window (inner-selected config), plus ensembles across families."""
    rows, probs, y_test = [], {}, None
    for family, window in PER_MODEL_WINDOWS.items():
        r, _, sel, y_test = run_task(df, test_season, window, 'none', families=[family], return_probs=True)
        rows += [x for x in r if x['role'] in ('selected', 'baseline_home')]
        probs[family] = sel[family]
    base = dict(test_season=test_season, window='per-model', weighting='none', n_test=len(y_test))
    for name, members in (('lr+lgbm', ['lr', 'lgbm']), ('lr+lgbm+mlp', ['lr', 'lgbm', 'mlp']),
                          ('lr+rf+lgbm+mlp', ['lr', 'rf', 'lgbm', 'mlp'])):
        p = np.mean([probs[m] for m in members], axis=0)
        rows.append({**base, 'role': 'ensemble', 'family': 'ensemble', 'config': name,
                     'n_fit': 0, 'val_logloss': np.nan, 'extra': '', **metrics(y_test, p)})
    # default logistic regression on all history as the reference baseline
    r, _ = run_task(df, test_season, 'all', 'none', families=['lr'])
    rows += [x for x in r if x['role'] == 'baseline_lr']
    return rows


def run_per_model(df, workers):
    seasons = sorted(df['season'].unique())
    tests = [s for s in seasons if s >= FIRST_TEST_SEASON]
    out = Parallel(n_jobs=workers)(delayed(run_per_model_season)(df, t) for t in tests)
    pd.DataFrame([r for rows in out for r in rows]).to_csv(PER_MODEL_CSV, index=False)
    print(f'Wrote {PER_MODEL_CSV}')


def per_model_report():
    d = pd.read_csv(PER_MODEL_CSV)
    d['name'] = np.where(d['role'] == 'selected', d['family'] + ' (' + d['window'] + ')', d['config'])
    d['name'] = np.where(d['role'] == 'ensemble', 'ensemble ' + d['config'], d['name'])
    lr = d[d['role'] == 'baseline_lr'].set_index('test_season')['logloss']
    d['diff_vs_lr'] = d['logloss'] - d['test_season'].map(lr)
    g = d.groupby(['role', 'name']).agg(
        logloss=('logloss', 'mean'), ll_std=('logloss', 'std'), brier=('brier', 'mean'), acc=('acc', 'mean'),
        mean_diff=('diff_vs_lr', 'mean'), wins=('diff_vs_lr', lambda s: int((s < 0).sum()))).reset_index()
    g['vs_lr'] = np.where(g['mean_diff'].abs() < TIE_MARGIN, 'tie', np.where(g['mean_diff'] < 0, 'better', 'worse'))
    return g.sort_values('logloss')


# ---------------------------------------------------------------- report

def md_table(df, floatfmt=None):
    cols = list(df.columns)
    lines = ['| ' + ' | '.join(cols) + ' |', '|' + '|'.join('---' for _ in cols) + '|']
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            cells.append(f'{v:.4f}' if isinstance(v, (float, np.floating)) else str(v))
        lines.append('| ' + ' | '.join(cells) + ' |')
    return '\n'.join(lines)


def summarize():
    folds = pd.read_csv(FOLDS_CSV)
    cal = pd.read_csv(CALIBRATION_CSV)
    key = ['role', 'family', 'config', 'window', 'weighting']
    n_folds = folds['test_season'].nunique()
    seasons = sorted(folds['test_season'].unique())

    # The config picked on the inner validation season can differ per fold, so those
    # roles are aggregated across folds as one entry; the picks are tabulated separately.
    picked = folds[folds['role'] == 'selected'].groupby(['family', 'config']).size().rename('times_picked').reset_index()
    per_fold_pick = folds['role'].isin(['selected', 'calibrated_platt', 'calibrated_isotonic'])
    folds.loc[per_fold_pick, 'config'] = 'inner-selected'
    cal = cal.copy()
    cal.loc[cal['role'].isin(['selected', 'calibrated_platt', 'calibrated_isotonic']), 'config'] = 'inner-selected'

    agg = folds.groupby(key).agg(
        logloss=('logloss', 'mean'), ll_std=('logloss', 'std'), brier=('brier', 'mean'),
        brier_std=('brier', 'std'), acc=('acc', 'mean'), acc_std=('acc', 'std'), folds=('logloss', 'size')
    ).reset_index()

    # paired differences against the default logistic regression at the same window/weighting
    lr = folds[folds['role'] == 'baseline_lr'].set_index(['test_season', 'window', 'weighting'])['logloss']
    folds = folds.join(lr.rename('lr_logloss'), on=['test_season', 'window', 'weighting'])
    folds['diff_vs_lr'] = folds['logloss'] - folds['lr_logloss']
    paired = folds.groupby(key).agg(mean_diff=('diff_vs_lr', 'mean'),
                                    wins=('diff_vs_lr', lambda s: int((s < 0).sum())),
                                    wins_by_margin=('diff_vs_lr', lambda s: int((s < -TIE_MARGIN).sum()))).reset_index()
    agg = agg.merge(paired, on=key)
    agg['vs_lr'] = np.where(agg['mean_diff'].abs() < TIE_MARGIN, 'tie',
                            np.where(agg['mean_diff'] < 0, 'better', 'worse'))
    agg.to_csv(RESULTS_DIR / 'config_summary.csv', index=False)

    show = ['role', 'family', 'config', 'window', 'weighting', 'logloss', 'll_std', 'brier', 'acc',
            'mean_diff', 'wins', 'vs_lr']
    L = []
    L.append('# Model comparison summary\n')
    L.append(f'All numbers are produced by `pipeline/model_comparison.py` from `results/folds.csv` '
             f'({n_folds} walk-forward folds, test seasons {seasons[0]} to {seasons[-1]}). '
             f'Log loss is the primary metric (lower is better). Differences under {TIE_MARGIN} log loss are '
             f'treated as ties. `mean_diff` is model minus default logistic regression at the same '
             f'window/weighting (negative = better); `wins` = folds where the model has lower log loss.\n')

    # data notes
    L.append('## Data notes and flags\n')
    if DROPS_CSV.exists():
        d = pd.read_csv(DROPS_CSV)
        L.append(f'Games dropped by the feature-building try/except, per season (total {int(d["dropped"].sum())} '
                 f'of {int(d["games"].sum())} games; zero-filled rows, where a team had no prior games in the '
                 f'lookback, total {int(d["zero_filled"].sum())}):\n')
        L.append(md_table(d) + '\n')
    if COVERAGE_CSV.exists():
        c = pd.read_csv(COVERAGE_CSV)
        L.append('Per-season data coverage (games with team stats / player box scores / inactive-player lists):\n')
        L.append(md_table(c) + '\n')
    L.append('Flags (not fixed):\n')
    L.append('- Inactive lists (`game_injuries`) are missing or partial in some seasons (see coverage table), so the '
             'injury features carry different information across seasons.\n'
             '- Training/test use each game\'s box-score inactive list, while live serving uses the current injury '
             'report: same idea, different source.\n'
             '- The player-value features use only box scores from days before the game, so no same-day leakage '
             'was found in them.\n'
             '- `all` window starts at 2005-06 (first season with inactive lists), not 1990.\n'
             '- LightGBM and MLP early stopping, and config selection, all use the inner validation season, so '
             'the validation log losses are slightly optimistic; test seasons are never used for tuning.\n')

    # leaderboard
    L.append('## Leaderboard (inner-selected, calibrated, ensembles, baselines), ranked by mean log loss\n')
    lb = agg[agg['role'] != 'candidate'].sort_values('logloss').head(40)
    L.append(md_table(lb[show]) + '\n')

    # per family best window/weighting
    L.append('## Recency: window x weighting per model family (inner-selected config, mean log loss)\n')
    for fam in ['lr', 'rf', 'lgbm', 'mlp']:
        s = agg[(agg['role'] == 'selected') & (agg['family'] == fam)]
        grid = s.pivot(index='window', columns='weighting', values='logloss')
        best = s.sort_values('logloss').iloc[0]
        ties = s[s['logloss'] <= best['logloss'] + TIE_MARGIN]
        L.append(f'### {fam}\n')
        L.append(md_table(grid.reset_index()) + '\n')
        L.append(f'Best: window={best["window"]}, weighting={best["weighting"]} '
                 f'(log loss {best["logloss"]:.4f}). Within {TIE_MARGIN} of best (ties): '
                 + ', '.join(f'{r.window}/{r.weighting}' for r in ties.itertuples()) + '.\n')

    L.append('Which config the inner validation season picked (count over all folds x windows x weightings):\n')
    L.append(md_table(picked) + '\n')

    # per-config table
    L.append('## Per-config results (every config refit on the full window; descriptive only)\n')
    L.append('Config choice for the headline numbers above is made on the inner validation season, not from '
             'this table. Showing window=all, weighting=none; the full grid is in `results/config_summary.csv`.\n')
    c = agg[(agg['role'] == 'candidate') & (agg['window'] == 'all') & (agg['weighting'] == 'none')].sort_values('logloss')
    L.append(md_table(c[show]) + '\n')

    # calibration
    L.append('## Calibration\n')
    cal_cmp = agg[agg['role'].isin(['selected', 'calibrated_platt', 'calibrated_isotonic'])]
    cal_cmp = cal_cmp.groupby(['family', 'role'])['logloss'].mean().unstack('role')
    L.append('Mean log loss across all window/weighting cells, uncalibrated (`selected`) vs calibrated on the '
             'inner validation season:\n')
    L.append(md_table(cal_cmp.reset_index()) + '\n')
    top = lb[lb['role'] == 'selected'].iloc[0] if (lb['role'] == 'selected').any() else lb.iloc[0]
    sel = cal[(cal['role'] == top['role']) & (cal['family'] == top['family']) & (cal['config'] == top['config'])
              & (cal['window'] == top['window']) & (cal['weighting'] == top['weighting'])]
    pooled = sel.groupby('bucket').apply(lambda g: pd.Series({
        'n': g['n'].sum(), 'avg_pred': np.average(g['avg_pred'], weights=g['n']),
        'actual': np.average(g['actual'], weights=g['n'])}), include_groups=False).reset_index()
    L.append(f'Reliability buckets for the best inner-selected model ({top["family"]}, window={top["window"]}, '
             f'weighting={top["weighting"]}), pooled across folds:\n')
    L.append(md_table(pooled) + '\n')

    if PER_MODEL_CSV.exists():
        L.append('## Final per-model setup (each family on its own training window, no recency weighting)\n')
        L.append('Windows: ' + ', '.join(f'{k}={v}' for k, v in PER_MODEL_WINDOWS.items()) +
                 '. Config per family is inner-selected on the validation season. `mean_diff` is against the '
                 'default logistic regression on all history.\n')
        L.append(md_table(per_model_report()) + '\n')

    SUMMARY_MD.write_text('\n'.join(L))
    print(f'Wrote {SUMMARY_MD}')


# ---------------------------------------------------------------- main

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--smoke', action='store_true')
    ap.add_argument('--summarize', action='store_true')
    ap.add_argument('--per-model', action='store_true', help='run each family on its own window, then summarize')
    ap.add_argument('--workers', type=int, default=11)
    args = ap.parse_args()

    RESULTS_DIR.mkdir(exist_ok=True)
    print(f'DB: {database.DB_PATH}')
    if args.summarize:
        summarize()
        sys.exit(0)

    df, drops = load_features(args.workers)
    if args.per_model:
        run_per_model(df, args.workers)
        if DROP_INJURIES or os.environ.get('PER_MODEL_OUT'):
            print(f'Features: {FEATURE_COLUMNS}')
            sys.exit(0)  # don't overwrite SUMMARY.md with a one-off run
        summarize()
        sys.exit(0)
    drops.to_csv(DROPS_CSV, index=False)
    write_coverage()
    print(f'{len(df)} feature rows, seasons {df["season"].min()}..{df["season"].max()}')
    run_all(df, args.workers, smoke=args.smoke)
    if not args.smoke:
        summarize()
