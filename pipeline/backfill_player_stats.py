"""Backfill per-player box score lines for games that have none, by re-fetching box scores.

Resumable: games already holding player rows are skipped, and attempted game ids are
logged to results/backfill_player_stats_done.txt (a page with no player table is not retried).
Newest games first.

Usage:
    NBA_DB_PATH=path/to/db python3 pipeline/backfill_player_stats.py [--since 2023-10-01]
"""

import argparse
import sqlite3
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / 'backend'))
sys.path.insert(0, str(REPO_ROOT / 'pipeline'))

import database
from config import TEAM_TO_ABBR, BOX_SCORES
from parsers import parse_player_game_stats
from utils import fetch_html, historical_abbr

DELAY_SECONDS = 4.0  # basketball-reference asks for at most ~20 requests/minute
PROGRESS_FILE = REPO_ROOT / 'results' / 'backfill_player_stats_done.txt'


def missing_games(since):
    conn = sqlite3.connect(database.DB_PATH)
    rows = conn.execute('''
        SELECT g.id, g.date, g.home_team, g.away_team FROM games g
        WHERE g.date >= ? AND NOT EXISTS (SELECT 1 FROM player_game_stats p WHERE p.game_id = g.id)
        ORDER BY g.date DESC
    ''', (since,)).fetchall()
    conn.close()
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--since', default='2023-10-01')
    args = ap.parse_args()

    database.create_database()
    PROGRESS_FILE.parent.mkdir(exist_ok=True)
    done = set(PROGRESS_FILE.read_text().split()) if PROGRESS_FILE.exists() else set()
    todo = [g for g in missing_games(args.since) if str(g[0]) not in done]
    print(f'DB: {database.DB_PATH}\n{len(todo)} games to try', flush=True)

    stored = failed = 0
    for k, (game_id, date, home, away) in enumerate(todo, 1):
        home_abbr = historical_abbr(home, date, TEAM_TO_ABBR)
        away_abbr = historical_abbr(away, date, TEAM_TO_ABBR)
        url = f'{BOX_SCORES}{date.replace("-", "")}0{home_abbr}.html'
        try:
            players = parse_player_game_stats(fetch_html(url, delay=DELAY_SECONDS), home_abbr, away_abbr)
        except Exception as e:
            failed += 1
            print(f'  FAILED {date} {home} vs {away}: {e}', flush=True)
            time.sleep(30)
            continue
        for side, team in (('home', home), ('away', away)):
            for row in players.get(side, []):
                database.insert_player_game_stats(game_id, team, row['player'], row)
        stored += 1
        with open(PROGRESS_FILE, 'a') as f:
            f.write(f'{game_id}\n')
        if k % 25 == 0:
            print(f'[{k}/{len(todo)}] {date}: {stored} stored, {failed} failed', flush=True)
    print(f'Done. {stored} stored, {failed} failed.')


if __name__ == '__main__':
    main()
