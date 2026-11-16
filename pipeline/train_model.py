"""Train a game-outcome model from SQLite using the same features as model_comparison.py.

Features (14) are built by model_comparison.build_season, so training and the
comparison harness cannot drift apart. Every feature uses only days BEFORE the
game date (rolling 7/30-day four factors, point-in-time injury value, back-to-back).

Two steps:
  1. Fit on every season before the last one, score on the last complete season
     (a held-out check, same as one walk-forward fold).
  2. Refit on all seasons through the last one and save that model.

The default model is plain logistic regression: in results/SUMMARY.md it tied or
beat every other single model. Use --model rf for the original random forest.

The saved pickle goes to results/trained_model.pkl by default. It is NOT written
to backend/models/ (the deployed model) unless you pass --out for that path.

Usage:
    NBA_DB_PATH=/path/to/full.db python3 pipeline/train_model.py [--model lr|rf] [--out PATH]
"""

import argparse
import pickle
import sys
from pathlib import Path

from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / 'backend'))
sys.path.insert(0, str(REPO_ROOT / 'pipeline'))

import model_comparison as mc

DEFAULT_OUT = REPO_ROOT / 'results' / 'trained_model.pkl'
SEED = mc.SEED


def make_model(kind):
    if kind == 'rf':
        return RandomForestClassifier(n_estimators=100, random_state=SEED, n_jobs=-1)
    return make_pipeline(LogisticRegression(max_iter=1000))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', choices=['lr', 'rf'], default='lr')
    parser.add_argument('--out', type=Path, default=DEFAULT_OUT)
    parser.add_argument('--workers', type=int, default=4)
    args = parser.parse_args()

    df, _ = mc.load_features(args.workers)
    test_season = mc.LAST_SEASON
    train = df[df['season'] < test_season]
    test = df[df['season'] == test_season]
    cols = mc.FEATURE_COLUMNS

    model = make_model(args.model).fit(train[cols], train['Home Win'])
    m = mc.metrics(test['Home Win'], model.predict_proba(test[cols])[:, 1])
    print(f'{args.model}: trained on {len(train)} games before {test_season}, '
          f'tested on {len(test)} games in {test_season}')
    print(f"  log loss {m['logloss']:.4f}  brier {m['brier']:.4f}  accuracy {m['acc'] * 100:.2f}%")

    final = make_model(args.model).fit(df[cols], df['Home Win'])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, 'wb') as f:
        pickle.dump({
            'model': final,
            'kind': args.model,
            'accuracy': m['acc'],
            'logloss': m['logloss'],
            'features': cols,
            'trained_through': mc.LAST_SEASON,
        }, f)
    print(f'Refit on {len(df)} games through {mc.LAST_SEASON}; model written to {args.out}')


if __name__ == '__main__':
    main()
