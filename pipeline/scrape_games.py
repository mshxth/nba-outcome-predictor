"""Live scraper: fetch new games and insert them into SQLite.

Idempotent -- checks database.game_exists() before fetching each game's box
score, so it's safe to re-run (e.g. nightly via GitHub Actions cron) and
only pulls what's new.

Usage:
    python3 pipeline/scrape_games.py                                # yesterday only
    python3 pipeline/scrape_games.py --start 2026-01-01 --end 2026-01-15
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

from bs4 import BeautifulSoup

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / 'backend'))
sys.path.insert(0, str(REPO_ROOT / 'pipeline'))

import database
from config import TEAM_TO_ABBR, BOX_SCORES, SCORES_BY_DATE
from parsers import parse_four_factors, parse_final_score, parse_inactive_players
from utils import fetch_html

ABBR_TO_TEAM = {abbr: team for team, abbr in TEAM_TO_ABBR.items()}


def date_range(start, end):
    d = datetime.strptime(start, '%Y-%m-%d')
    end_d = datetime.strptime(end, '%Y-%m-%d')
    while d <= end_d:
        yield d.strftime('%Y-%m-%d')
        d += timedelta(days=1)


def scrape_date(date):
    """Scrape one date's scoreboard and insert any games not already stored.

    Returns (inserted_count, games_found_count).
    """
    year, month, day = date.split('-')
    url = SCORES_BY_DATE.format(int(month), int(day), int(year))
    html = fetch_html(url)
    soup = BeautifulSoup(html, 'html.parser')
    games = soup.find_all('div', class_='game_summary expanded nohover')

    inserted = 0
    for game in games:
        home_team = game.find('table', class_='teams').find_all('tr')[1].find_all('td')[0].find('a').get_text().strip()
        away_team = game.find('table', class_='teams').find_all('tr')[0].find_all('td')[0].find('a').get_text().strip()

        if database.game_exists(date, home_team, away_team):
            continue

        game_url = game.find('td', class_='right gamelink').find('a')['href'][11:]
        box_html = fetch_html(BOX_SCORES + game_url)

        factors = parse_four_factors(box_html)
        if factors is None:
            print(f'  WARNING: no four-factors data for {date} {home_team} vs {away_team}, skipping')
            continue

        home_score, away_score, home_win = parse_final_score(box_html)
        inactives = parse_inactive_players(box_html)

        game_id = database.insert_game(date, home_team, away_team, home_score, away_score, home_win)
        database.insert_team_stats(
            game_id, home_team, 1,
            factors['home']['off_rtg'], factors['away']['off_rtg'],
            factors['home']['efg_pct'], factors['away']['efg_pct'],
            factors['home']['tov_pct'], factors['away']['tov_pct'],
            factors['home']['orb_pct'], factors['away']['orb_pct'],
        )
        database.insert_team_stats(
            game_id, away_team, 0,
            factors['away']['off_rtg'], factors['home']['off_rtg'],
            factors['away']['efg_pct'], factors['home']['efg_pct'],
            factors['away']['tov_pct'], factors['home']['tov_pct'],
            factors['away']['orb_pct'], factors['home']['orb_pct'],
        )

        home_abbr = TEAM_TO_ABBR.get(home_team)
        away_abbr = TEAM_TO_ABBR.get(away_team)
        if home_abbr in inactives:
            database.insert_game_injuries(game_id, home_team, inactives[home_abbr])
        if away_abbr in inactives:
            database.insert_game_injuries(game_id, away_team, inactives[away_abbr])

        inserted += 1

    return inserted, len(games)


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser()
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    arg_parser.add_argument('--start', default=yesterday)
    arg_parser.add_argument('--end', default=yesterday)
    args = arg_parser.parse_args()

    database.create_database()

    total_inserted, total_found = 0, 0
    for date in date_range(args.start, args.end):
        inserted, found = scrape_date(date)
        total_inserted += inserted
        total_found += found
        print(f'{date}: {inserted} new games inserted (of {found} found)')

    print(f'Done. {total_inserted} new games inserted total (of {total_found} found across range).')
