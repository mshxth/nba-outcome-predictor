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
    "Washington": "WAS"
}


# URLs
BOX_SCORES = "https://www.basketball-reference.com/boxscores/"
SCORES_BY_DATE = BOX_SCORES + "?month={}&day={}&year={}"
TEAMS = "https://www.basketball-reference.com/teams/"


# Date utility functions
def get_last_7_days_from_date(date):
    date = datetime.strptime(date, '%Y-%m-%d')
    last_7_days = [(date - timedelta(days=i+1)).strftime('%Y-%m-%d') for i in range(7)]
    return last_7_days

def get_last_15_days_from_date(date):
    date = datetime.strptime(date, '%Y-%m-%d')
    last_15_days = [(date - timedelta(days=i+1)).strftime('%Y-%m-%d') for i in range(15)]
    return last_15_days

def get_last_30_days_from_date(date):
    date = datetime.strptime(date, '%Y-%m-%d')
    last_30_days = [(date - timedelta(days=i+1)).strftime('%Y-%m-%d') for i in range(30)]
    return last_30_days

def get_2023_2024_season_dates():
    start_date = datetime(2023, 10, 24)
    end_date = datetime(2024, 4, 14)
    date_range = [(start_date + timedelta(days=i)).strftime('%Y-%m-%d') for i in range((end_date - start_date).days + 1)]
    return date_range

def get_2024_2025_season_dates():
    start_date = datetime(2024, 10, 22)
    end_date = datetime(2025, 4, 13)
    date_range = [(start_date + timedelta(days=i)).strftime('%Y-%m-%d') for i in range((end_date - start_date).days + 1)]
    return date_range