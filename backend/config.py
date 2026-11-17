"""Configuration, constants, and utility functions - EXACT from notebook."""

from datetime import datetime, timedelta

# Team city to abbreviation mapping
TEAM_TO_ABBR = {
    "Atlanta": "ATL",
    "Boston": "BOS",
    "Brooklyn": "BRK",
    "Charlotte": "CHO",
    "Chicago": "CHI",
    "Cleveland": "CLE",
    "Dallas": "DAL",
    "Denver": "DEN",
    "Detroit": "DET",
    "Golden State": "GSW",
    "Houston": "HOU",
    "Indiana": "IND",
    "LA Clippers": "LAC",
    "LA Lakers": "LAL",
    "Memphis": "MEM",
    "Miami": "MIA",
    "Milwaukee": "MIL",
    "Minnesota": "MIN",
    "New Orleans": "NOP",
    "New York": "NYK",
    "Oklahoma City": "OKC",
    "Orlando": "ORL",
    "Philadelphia": "PHI",
    "Phoenix": "PHO",
    "Portland": "POR",
    "Sacramento": "SAC",
    "San Antonio": "SAS",
    "Toronto": "TOR",
    "Utah": "UTA",
    "Washington": "WAS",
    # Historical-only franchise names (relocated/renamed since 2007-08) --
    # needed to backfill seasons before the moves below. See
    # pipeline/utils.py:historical_abbr for the date-based overrides this
    # doesn't cover (Charlotte and New Orleans kept their city name but
    # changed abbreviation).
    "Seattle": "SEA",       # -> Oklahoma City Thunder, 2008-09
    "New Jersey": "NJN",    # -> Brooklyn Nets, 2012-13
    # New Orleans Hornets played as a displaced dual-city franchise for two
    # seasons after Hurricane Katrina (2005-06, 2006-07) before returning to
    # New Orleans full-time in 2007-08 -- a genuinely distinct team identity
    # on basketball-reference, not just a renamed abbreviation.
    "New Orleans/Oklahoma City": "NOK",
    "Vancouver": "VAN",     # -> Memphis Grizzlies, 2001-02
}

# The 30 teams that exist today (everything except the historical-only names above).
# Live code (API validation, live scrapers) must use this, not TEAM_TO_ABBR.
HISTORICAL_TEAMS = {"Seattle", "New Jersey", "New Orleans/Oklahoma City", "Vancouver"}
CURRENT_TEAMS = [team for team in TEAM_TO_ABBR if team not in HISTORICAL_TEAMS]


# URLs
BOX_SCORES = "https://www.basketball-reference.com/boxscores/"
SCORES_BY_DATE = BOX_SCORES + "?month={}&day={}&year={}"
TEAMS = "https://www.basketball-reference.com/teams/"


# Date utility functions
def get_last_n_days_from_date(date, n):
    date = datetime.strptime(date, '%Y-%m-%d')
    return [(date - timedelta(days=i + 1)).strftime('%Y-%m-%d') for i in range(n)]


def get_season_start_date(date):
    """A safe lower bound for 'this season so far' as of `date` -- August 1 of the
    season's start year (NBA seasons start mid-to-late October at the earliest,
    so this comfortably predates any real games while staying within the same season).
    """
    d = datetime.strptime(date, '%Y-%m-%d')
    start_year = d.year if d.month >= 10 else d.year - 1
    return f'{start_year}-08-01'