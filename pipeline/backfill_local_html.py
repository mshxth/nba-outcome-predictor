"""One-time backfill: ingest already-downloaded local HTML into the SQLite schema.

Walks the gitignored, local-only GAMES/ and backend/TEAMS/ folders (raw HTML
already scraped by the old notebook pipeline) and parses+inserts everything
into backend/data/nba_data.db using pipeline/parsers.py + backend/database.py.

This exists so the ~3,000 games already scraped don't need to be re-fetched
from basketball-reference.com through the new live scrapers -- it's a bridge
from "what was already manually collected" to the new automated system.

Run once: python3 pipeline/backfill_local_html.py
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / 'backend'))
sys.path.insert(0, str(REPO_ROOT / 'pipeline'))

import database
from config import TEAM_TO_ABBR
from parsers import (
    parse_four_factors, parse_final_score, parse_inactive_players,
    parse_team_per_game_stats, parse_team_advanced_stats, parse_team_injuries,
)
from utils import read_legacy_html

ABBR_TO_TEAM = {abbr: team for team, abbr in TEAM_TO_ABBR.items()}

GAMES_DIR = REPO_ROOT / 'GAMES'
TEAMS_DIR = REPO_ROOT / 'backend' / 'TEAMS'

# The team pages were scraped as a single 2024-25 season snapshot (notebook
# fetched ".../{ABBR}/2025.html"); label backfilled player stats accordingly.
BACKFILL_SEASON = '2024-25'


def parse_game_filename(filename):
    """Split "{date}-{home}-{away}.html" into (date, home, away).

    No NBA city name contains a hyphen, so splitting on "-" always yields
    exactly 5 parts: year, month, day, home, away.
    """
    parts = filename[:-len('.html')].split('-')
    date = '-'.join(parts[:3])
    home, away = parts[3], parts[4]
    return date, home, away


def backfill_games():
    """Parse every box score in GAMES/ and insert into games/team_stats/game_injuries."""
    if not GAMES_DIR.exists():
        print(f'No GAMES/ folder found at {GAMES_DIR}, skipping game backfill.')
        return

    files = sorted(p for p in GAMES_DIR.iterdir() if p.suffix == '.html')
    inserted, skipped, failed = 0, 0, 0

    for path in files:
        date, home, away = parse_game_filename(path.name)

        if database.game_exists(date, home, away):
            skipped += 1
            continue

        try:
            html = read_legacy_html(path)
            factors = parse_four_factors(html)
            home_score, away_score, home_win = parse_final_score(html)
            inactives = parse_inactive_players(html)

            if factors is None:
                raise ValueError('four-factors table not found')

            game_id = database.insert_game(date, home, away, home_score, away_score, home_win)

            database.insert_team_stats(
                game_id, home, 1,
                factors['home']['off_rtg'], factors['away']['off_rtg'],
                factors['home']['efg_pct'], factors['away']['efg_pct'],
                factors['home']['tov_pct'], factors['away']['tov_pct'],
                factors['home']['orb_pct'], factors['away']['orb_pct'],
            )
            database.insert_team_stats(
                game_id, away, 0,
                factors['away']['off_rtg'], factors['home']['off_rtg'],
                factors['away']['efg_pct'], factors['home']['efg_pct'],
                factors['away']['tov_pct'], factors['home']['tov_pct'],
                factors['away']['orb_pct'], factors['home']['orb_pct'],
            )

            home_abbr = TEAM_TO_ABBR.get(home)
            away_abbr = TEAM_TO_ABBR.get(away)
            if home_abbr in inactives:
                database.insert_game_injuries(game_id, home, inactives[home_abbr])
            if away_abbr in inactives:
                database.insert_game_injuries(game_id, away, inactives[away_abbr])

            inserted += 1
        except Exception as e:
            failed += 1
            print(f'  FAILED {path.name}: {e}')

    print(f'Games: {inserted} inserted, {skipped} already present, {failed} failed (of {len(files)} files)')


def backfill_teams():
    """Parse every team page in backend/TEAMS/ and insert into player_season_stats/current_injuries."""
    if not TEAMS_DIR.exists():
        print(f'No backend/TEAMS/ folder found at {TEAMS_DIR}, skipping team backfill.')
        return

    files = sorted(p for p in TEAMS_DIR.iterdir() if p.suffix == '.html')
    scraped_at = datetime.now(timezone.utc).isoformat()

    for path in files:
        abbr = path.stem
        team = ABBR_TO_TEAM.get(abbr)
        if not team:
            print(f'  SKIPPED {path.name}: unknown team abbreviation')
            continue

        html = read_legacy_html(path)
        per_game = parse_team_per_game_stats(html)
        advanced = parse_team_advanced_stats(html)
        injuries = parse_team_injuries(html)

        all_players = set(per_game) | set(advanced)
        for player in all_players:
            pg = per_game.get(player, {})
            adv = advanced.get(player, {})
            database.upsert_player_season_stats(
                team, player, BACKFILL_SEASON,
                pg.get('ppg'), pg.get('rpg'), pg.get('apg'), pg.get('spg'), pg.get('bpg'),
                adv.get('vorp'), adv.get('ws'),
                scraped_at,
            )

        database.replace_current_injuries(team, injuries, scraped_at)
        print(f'  {team}: {len(all_players)} players, {len(injuries)} current injuries')

    print(f'Teams: {len(files)} team pages processed')


if __name__ == '__main__':
    database.create_database()
    print('Backfilling games...')
    backfill_games()
    print('Backfilling teams...')
    backfill_teams()
