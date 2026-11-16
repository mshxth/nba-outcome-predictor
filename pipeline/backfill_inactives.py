"""Backfill missing inactive-player lists (game_injuries) by re-fetching box scores.

Some seasons were loaded without inactive lists even though basketball-reference
has them on every box score page. This finds every game since FIRST_DATE that has
no game_injuries rows, re-fetches its box score, and stores the parsed lists.

Safe to stop and re-run: every attempted game id is appended to a progress file,
so a re-run only does games it hasn't tried yet. A game with a genuinely empty
inactive list is also recorded as tried, so it isn't re-fetched.

Newest games first, since recent seasons matter most for the model.

Usage:
    NBA_DB_PATH=~/nba-data/nba_data_full.db python3 pipeline/backfill_inactives.py
"""

import sqlite3
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / 'backend'))
sys.path.insert(0, str(REPO_ROOT / 'pipeline'))

import database
from config import TEAM_TO_ABBR, BOX_SCORES
from parsers import parse_inactive_players
from utils import fetch_html, historical_abbr

FIRST_DATE = '2005-10-01'  # first season with inactive lists
DELAY_SECONDS = 4.0        # basketball-reference asks for at most ~20 requests/minute
PROGRESS_FILE = REPO_ROOT / 'results' / 'backfill_inactives_done.txt'


def games_missing_inactives():
    conn = sqlite3.connect(database.DB_PATH)
    rows = conn.execute('''
        SELECT g.id, g.date, g.home_team, g.away_team FROM games g
        WHERE g.date >= ? AND NOT EXISTS (SELECT 1 FROM game_injuries i WHERE i.game_id = g.id)
        ORDER BY g.date DESC
    ''', (FIRST_DATE,)).fetchall()
    conn.close()
    return rows


def fetch_with_retry(url):
    for attempt in range(3):
        try:
            return fetch_html(url, delay=DELAY_SECONDS)
        except Exception as e:
            wait = 120 * (attempt + 1)
            print(f'  fetch failed ({e}); waiting {wait}s', flush=True)
            time.sleep(wait)
    raise RuntimeError(f'giving up on {url}')


def main():
    PROGRESS_FILE.parent.mkdir(exist_ok=True)
    done = set(PROGRESS_FILE.read_text().split()) if PROGRESS_FILE.exists() else set()
    todo = [g for g in games_missing_inactives() if str(g[0]) not in done]
    print(f'DB: {database.DB_PATH}\n{len(todo)} games to try ({len(done)} already tried)', flush=True)

    stored, empty, failed = 0, 0, 0
    for k, (game_id, date, home, away) in enumerate(todo, 1):
        home_abbr = historical_abbr(home, date, TEAM_TO_ABBR)
        away_abbr = historical_abbr(away, date, TEAM_TO_ABBR)
        url = f'{BOX_SCORES}{date.replace("-", "")}0{home_abbr}.html'
        try:
            inactives = parse_inactive_players(fetch_with_retry(url))
        except Exception as e:
            failed += 1
            print(f'  FAILED {date} {home} vs {away}: {e}', flush=True)
            continue  # not recorded as tried, so a re-run retries it

        found = False
        for team, abbr in ((home, home_abbr), (away, away_abbr)):
            if inactives.get(abbr):
                database.insert_game_injuries(game_id, team, inactives[abbr])
                found = True
        stored += found
        empty += not found
        with open(PROGRESS_FILE, 'a') as f:
            f.write(f'{game_id}\n')
        if k % 50 == 0:
            print(f'[{k}/{len(todo)}] {date}: {stored} stored, {empty} empty, {failed} failed', flush=True)

    print(f'Done. {stored} stored, {empty} with no inactives listed, {failed} failed.')


if __name__ == '__main__':
    main()
