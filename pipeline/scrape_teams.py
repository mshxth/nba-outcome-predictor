"""Live scraper: refresh player season stats (and current injuries, if basketball-reference
ever brings that section back -- see pipeline/parsers.py:parse_team_injuries).

Idempotent by design -- player_season_stats is upserted keyed on
(team, player, season), and current_injuries is fully replaced per team each
run, so re-running just refreshes the same rows.

Usage:
    python3 pipeline/scrape_teams.py
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / 'backend'))
sys.path.insert(0, str(REPO_ROOT / 'pipeline'))

import database
from config import TEAM_TO_ABBR, TEAMS
from parsers import parse_team_per_game_stats, parse_team_advanced_stats, parse_team_injuries
from utils import fetch_html


def current_season_label(today=None):
    """NBA season label for today's date, e.g. '2025-26'. Season starts in October."""
    today = today or datetime.now()
    start_year = today.year if today.month >= 10 else today.year - 1
    return f'{start_year}-{str(start_year + 1)[-2:]}'


def current_season_page_year(today=None):
    """basketball-reference team-page URLs use the season's END year (e.g. 2026 for 2025-26)."""
    today = today or datetime.now()
    return today.year + 1 if today.month >= 10 else today.year


def scrape_team(team, season):
    abbr = TEAM_TO_ABBR[team]
    year = current_season_page_year()
    url = f'{TEAMS}{abbr}/{year}.html'
    html = fetch_html(url)

    per_game = parse_team_per_game_stats(html)
    advanced = parse_team_advanced_stats(html)
    injuries = parse_team_injuries(html)

    scraped_at = datetime.now(timezone.utc).isoformat()
    all_players = set(per_game) | set(advanced)
    for player in all_players:
        pg = per_game.get(player, {})
        adv = advanced.get(player, {})
        database.upsert_player_season_stats(
            team, player, season,
            pg.get('ppg'), pg.get('rpg'), pg.get('apg'), pg.get('spg'), pg.get('bpg'),
            adv.get('vorp'), adv.get('ws'),
            scraped_at,
        )

    database.replace_current_injuries(team, injuries, scraped_at)
    return len(all_players), len(injuries)


if __name__ == '__main__':
    database.create_database()
    season = current_season_label()

    for team in TEAM_TO_ABBR:
        players, injuries = scrape_team(team, season)
        print(f'{team}: {players} players, {injuries} current injuries')

    print('Done.')
