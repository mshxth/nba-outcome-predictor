"""Train the Random Forest game-outcome model directly from SQLite.

Reproduces the notebook's original feature-building and training
methodology exactly (see NBA.ipynb cells 46/50/53 -- this script doesn't
change the modeling approach, only where the data comes from):
  - training features (2023-24 season) use each game's own raw four-factor
    stats
  - test features (2024-25 season) use rolling 7/30-day averages, the same
    as live serving
  - both use each game's actual per-game injury list (game_injuries table)

Usage:
    python3 pipeline/train_model.py
"""

import pickle
import sqlite3
import sys
from pathlib import Path

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / 'backend'))

import database
from config import get_2023_2024_season_dates, get_2024_2025_season_dates
from data import (
    get_avg_rtgs, get_avg_efgs, get_avg_tovs, get_avg_orbs, get_input_format,
    get_injury_value, get_injury_advanced,
)

MODEL_PATH = REPO_ROOT / 'backend' / 'models' / 'trained_model.pkl'

FEATURE_COLUMNS = [
    'Home ORtg', 'Away ORtg', 'Home eFG%', 'Away eFG%',
    'Home TOV%', 'Away TOV%', 'Home ORB%', 'Away ORB%',
    'Home Injury Value', 'Away Injury Value',
    'Home Injury Advanced', 'Away Injury Advanced',
]


def _games_in_range(dates):
    conn = sqlite3.connect(database.DB_PATH)
    cursor = conn.cursor()
    placeholders = ','.join('?' * len(dates))
    cursor.execute(f'''
        SELECT id, date, home_team, away_team, home_win
        FROM games WHERE date IN ({placeholders})
        ORDER BY date
    ''', dates)
    rows = cursor.fetchall()
    conn.close()
    return rows


def _raw_four_factors(game_id, team):
    conn = sqlite3.connect(database.DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT off_rtg, efg_pct, tov_pct, orb_pct FROM team_stats
        WHERE game_id = ? AND team = ?
    ''', (game_id, team))
    row = cursor.fetchone()
    conn.close()
    return row


def _injury_features(game_id, home, away):
    home_injuries = database.get_game_injuries(game_id, home)
    away_injuries = database.get_game_injuries(game_id, away)
    return {
        'Home Injury Value': get_injury_value(home_injuries, home),
        'Away Injury Value': get_injury_value(away_injuries, away),
        'Home Injury Advanced': get_injury_advanced(home_injuries, home),
        'Away Injury Advanced': get_injury_advanced(away_injuries, away),
    }


def build_training_rows():
    rows = []
    for game_id, date, home, away, home_win in _games_in_range(get_2023_2024_season_dates()):
        home_stats = _raw_four_factors(game_id, home)
        away_stats = _raw_four_factors(game_id, away)
        if not home_stats or not away_stats:
            continue

        rows.append({
            'Home ORtg': home_stats[0], 'Away ORtg': away_stats[0],
            'Home eFG%': home_stats[1], 'Away eFG%': away_stats[1],
            'Home TOV%': home_stats[2], 'Away TOV%': away_stats[2],
            'Home ORB%': home_stats[3], 'Away ORB%': away_stats[3],
            **_injury_features(game_id, home, away),
            'Home Win': home_win,
        })
    return pd.DataFrame(rows)


def build_test_rows():
    rows = []
    for game_id, date, home, away, home_win in _games_in_range(get_2024_2025_season_dates()):
        try:
            home_rtg, away_rtg = get_input_format(date, home, away, get_avg_rtgs)
            home_efg, away_efg = get_input_format(date, home, away, get_avg_efgs)
            home_tov, away_tov = get_input_format(date, home, away, get_avg_tovs)
            home_orb, away_orb = get_input_format(date, home, away, get_avg_orbs)
        except Exception:
            continue

        rows.append({
            'Home ORtg': home_rtg, 'Away ORtg': away_rtg,
            'Home eFG%': home_efg, 'Away eFG%': away_efg,
            'Home TOV%': home_tov, 'Away TOV%': away_tov,
            'Home ORB%': home_orb, 'Away ORB%': away_orb,
            **_injury_features(game_id, home, away),
            'Home Win': home_win,
        })
    return pd.DataFrame(rows)


if __name__ == '__main__':
    print('Building training data (2023-24 season, raw per-game stats)...')
    df_train = build_training_rows()
    print(f'{len(df_train)} training rows')

    print('Building test data (2024-25 season, rolling averages)...')
    df_test = build_test_rows()
    print(f'{len(df_test)} test rows')

    X_train, y_train = df_train[FEATURE_COLUMNS], df_train['Home Win']
    X_test, y_test = df_test[FEATURE_COLUMNS], df_test['Home Win']

    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f'Test accuracy: {accuracy * 100:.2f}%  (notebook baseline: 65.47%)')

    MODEL_PATH.parent.mkdir(exist_ok=True)
    with open(MODEL_PATH, 'wb') as f:
        pickle.dump({
            'model': model,
            'accuracy': accuracy,
            'features': FEATURE_COLUMNS,
        }, f)

    print(f'Model written to {MODEL_PATH}')
