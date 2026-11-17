"""Train the deployed game-outcome model from SQLite, with no leakage.

Every feature is built by model_comparison.build_season using only games played
BEFORE the game date. Nothing from the game being predicted -- its own box score,
final stats -- is used as an input. Deployed features (10):
  - four factors (ORtg, eFG%, TOV%, ORB%) x home/away: rolling 7/30-day team average
    blended with the opponent's allowed average
  - back-to-back x home/away

Pass --with-injuries for the 14-feature research version, which adds point-in-time
Injury Value / Injury Advanced (home/away) from player_game_stats. For logistic
regression it was a tie with the 10-feature model (see results/SUMMARY.md and
results/per_model_no_injuries.csv), and it needs per-player stats in the database.

Two steps:
  1. Fit on every season before the last complete one, score on that season
     (a held-out check, same as one walk-forward fold).
  2. Refit on every game in the database and save that model.

The default model is logistic regression: in results/SUMMARY.md it tied or beat
every other single model. Use --model rf for a random forest.

Usage (this is what the weekly GitHub Action runs):
    python3 pipeline/train_model.py
"""

import argparse
import os
import pickle
import sys
from pathlib import Path

# Must be decided before model_comparison is imported (it picks the feature list at import).
if '--with-injuries' not in sys.argv:
    os.environ['DROP_INJURIES'] = '1'

from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / 'backend'))
sys.path.insert(0, str(REPO_ROOT / 'pipeline'))

import database
import model_comparison as mc
from utils import season_label_for_date

MODEL_PATH = REPO_ROOT / 'backend' / 'models' / 'trained_model.pkl'
SEED = mc.SEED


def make_model(kind):
    if kind == 'rf':
        return RandomForestClassifier(n_estimators=100, random_state=SEED, n_jobs=-1)
    # Standardized: the injury features are in the hundreds while the four factors are ~0.5-120.
    return make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))


def latest_season_in_db():
    import sqlite3
    conn = sqlite3.connect(database.DB_PATH)
    latest = conn.execute('SELECT MAX(date) FROM games').fetchone()[0]
    conn.close()
    return season_label_for_date(latest)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', choices=['lr', 'rf'], default='lr')
    parser.add_argument('--out', type=Path, default=MODEL_PATH)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--with-injuries', action='store_true')
    args = parser.parse_args()

    cols = mc.FEATURE_COLUMNS
    latest = latest_season_in_db()
    print(f'DB: {database.DB_PATH}\nFeatures ({len(cols)}): {cols}\nLatest season in DB: {latest}')
    df, drops = mc.load_features(args.workers, last_season=latest)
    if drops['dropped'].sum() > 0.02 * (drops['games'].sum()):
        raise SystemExit(f"{int(drops['dropped'].sum())} of {int(drops['games'].sum())} games could not be "
                         f"featurized (missing player stats?). Refusing to train.\n{drops.to_string(index=False)}")

    # Held-out check: the last season that is complete (everything before the latest, partial one).
    seasons = sorted(df['season'].unique())
    complete = [s for s in seasons if s < latest]
    test_season = complete[-1]
    train, test = df[df['season'] < test_season], df[df['season'] == test_season]
    model = make_model(args.model).fit(train[cols], train['Home Win'])
    m = mc.metrics(test['Home Win'], model.predict_proba(test[cols])[:, 1])
    print(f'{args.model}: trained on {len(train)} games from {train["season"].min()} to '
          f'{train["season"].max()}, tested on {len(test)} games in {test_season}')
    print(f"  log loss {m['logloss']:.4f}  brier {m['brier']:.4f}  accuracy {m['acc'] * 100:.2f}%")

    final = make_model(args.model).fit(df[cols], df['Home Win'])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, 'wb') as f:
        pickle.dump({
            'model': final,
            'kind': args.model,
            'accuracy': m['acc'],
            'logloss': m['logloss'],
            'test_season': test_season,
            'features': cols,
            'trained_through': str(df['date'].max()),
            'n_games': len(df),
        }, f)
    print(f'Refit on {len(df)} games through {df["date"].max()}; model written to {args.out}')


if __name__ == '__main__':
    main()
