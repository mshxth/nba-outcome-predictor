"""Train the deployed game-outcome model from SQLite, with no leakage.

Every feature is built by model_comparison.build_season using only games played
BEFORE the game date (rolling 7/30-day four factors blended with the opponent's
allowed stats, plus back-to-back flags). Nothing from the game being predicted
-- its own box score, final stats or inactive list -- is used as an input.

Default features (10): the four factors x home/away, and back-to-back x home/away.
The per-game injury features need the player_game_stats table, which only exists in
the large research database, so they are off by default. Pass --with-injuries to use
them when pointing NBA_DB_PATH at a database that has that table (research only: the
live backend cannot serve those features).

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
    return make_pipeline(LogisticRegression(max_iter=1000))


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
    df, _ = mc.load_features(args.workers, last_season=latest)

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
