"""Shared utilities for the pipeline scripts."""

import time
from datetime import datetime

import requests
from fake_useragent import UserAgent

_ua = UserAgent()


def season_label_for_date(date_str):
    """NBA season label for a game date, e.g. '2023-10-24' -> '2023-24'.

    Season starts in October, so any date from October through the following
    September belongs to the season that started that October.
    """
    date = datetime.strptime(date_str, '%Y-%m-%d')
    start_year = date.year if date.month >= 10 else date.year - 1
    return f'{start_year}-{str(start_year + 1)[-2:]}'


# Franchises that kept their city name but changed abbreviation on
# basketball-reference: the original Charlotte Hornets (CHH) relocated to
# New Orleans for the 2002-03 season; Charlotte got an expansion team, the
# Bobcats (CHA), in 2004-05, which was renamed the Hornets (CHO) in 2014-15;
# New Orleans Hornets (NOH) became the Pelicans (NOP) in 2013-14; Washington
# Bullets (WSB) were renamed the Wizards (WAS) starting 1997-98. Checked in
# order, first match wins, so earlier cutoffs must come first. Franchises
# that also changed city name (Seattle -> OKC, New Jersey -> Brooklyn,
# Vancouver -> Memphis) are handled by config.TEAM_TO_ABBR having entries for
# both the old and current city names instead.
_HISTORICAL_ABBR_OVERRIDES = [
    ('Charlotte', '2002-10-01', 'CHH'),
    ('Charlotte', '2014-10-01', 'CHA'),
    ('New Orleans', '2013-10-01', 'NOH'),
    ('Washington', '1997-10-01', 'WSB'),
]


def historical_abbr(team, date, team_to_abbr):
    """basketball-reference's abbreviation for `team` as of `date`.

    team_to_abbr is the current-day config.TEAM_TO_ABBR map; only used as a
    fallback when no historical override applies.
    """
    for override_team, before_date, abbr in _HISTORICAL_ABBR_OVERRIDES:
        if team == override_team and date < before_date:
            return abbr
    return team_to_abbr.get(team)


def fetch_html(url, delay=3.0):
    """Fetch a page from basketball-reference.com.

    Forces UTF-8 decoding -- by default `requests` guesses the response
    encoding and guesses wrong for these pages, which silently mangles
    accented player names. Includes a polite delay so scraping doesn't
    hammer the site.
    """
    headers = {'User-Agent': _ua.random}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    resp.encoding = 'utf-8'
    if delay:
        time.sleep(delay)
    return resp.text
