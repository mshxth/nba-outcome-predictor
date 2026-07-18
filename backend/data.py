"""Data functions using SQLite database instead of HTML parsing."""

from datetime import datetime, timedelta
from functools import lru_cache
from config import get_last_30_days_from_date, get_last_7_days_from_date
from database import (
    get_team_stats_for_dates, get_home_win, check_back_to_back,
    get_latest_player_season_stats, get_current_injuries, get_game_injuries,
)


# ===== FUNCTIONS THAT NOW USE SQLITE =====

def get_metrics(dates, team, metric_name):
    """Get metrics for dates using SQLite."""
    return get_team_stats_for_dates(team, dates, metric_name)


def get_avg_metrics(dates, team, metric_name):
    """Calculate avg metrics with lookback using SQLite."""
    team_metric = 0
    opp_metric = 0
    count = 0
    metrics = get_metrics(dates, team, metric_name)
    
    for metric in metrics:
        if metric:
            team_metric += metric[0]
            opp_metric += metric[1]
            count += 1

    if count < 10:
        earliest_date = dates[-1]
        date_obj = datetime.strptime(earliest_date, '%Y-%m-%d')
        
        days_back = 30
        while count < 10 and days_back <= 200:
            expanded_dates = [(date_obj - timedelta(days=i)).strftime('%Y-%m-%d') 
                             for i in range(days_back, days_back + 30)]
            
            additional_metrics = get_metrics(expanded_dates, team, metric_name)
            
            for metric in additional_metrics:
                if metric:
                    team_metric += metric[0]
                    opp_metric += metric[1]
                    count += 1
                    if count >= 10:
                        break
            
            days_back += 30
    
    if count == 0:
        return [0, 0]
    
    team_metric /= count
    opp_metric /= count
    return [team_metric, opp_metric]


def get_avg_rtgs(dates, team):
    """Get avg offensive ratings using SQLite."""
    return get_avg_metrics(dates, team, 'off_rtg')


def get_avg_efgs(dates, team):
    """Get avg effective FG% using SQLite."""
    return get_avg_metrics(dates, team, 'efg_pct')


def get_avg_tovs(dates, team):
    """Get avg turnover % using SQLite."""
    return get_avg_metrics(dates, team, 'tov_pct')


def get_avg_orbs(dates, team):
    """Get avg offensive rebound % using SQLite."""
    return get_avg_metrics(dates, team, 'orb_pct')


def scrape_home_win(date, home, away):
    """Check if home won using SQLite."""
    result = get_home_win(date, home, away)
    return result if result is not None else 0


def scrape_back_to_back(date, home, away):
    """Check back to back using SQLite."""
    homeb2b = check_back_to_back(date, home)
    awayb2b = check_back_to_back(date, away)
    return homeb2b, awayb2b


def get_input_format(date, home, away, func):
    """Helper function to get proper format for input."""
    home_30_days_avgs = func(get_last_30_days_from_date(date), home)
    away_30_days_avgs = func(get_last_30_days_from_date(date), away)
    home_30_days = (home_30_days_avgs[0] + away_30_days_avgs[1]) / 2
    away_30_days = (away_30_days_avgs[0] + home_30_days_avgs[1]) / 2

    home_7_days_avgs = func(get_last_7_days_from_date(date), home)
    away_7_days_avgs = func(get_last_7_days_from_date(date), away)
    home_7_days = (home_7_days_avgs[0] + away_7_days_avgs[1]) / 2
    away_7_days = (away_7_days_avgs[0] + home_7_days_avgs[1]) / 2 
  
    home_ret = (home_30_days + home_7_days) / 2
    away_ret = (away_30_days + away_7_days) / 2
   
    return home_ret, away_ret


# ===== INJURY/PLAYER-VALUE FUNCTIONS (DB-backed, replaces HTML parsing at request time) =====

def get_player_value(ppg, rpg, apg, spg, bpg):
    """Calculate player value from stats."""
    return ppg + (1.2 * rpg) + (1.5 * apg) + (2 * spg) + (2 * bpg)


@lru_cache(maxsize=64)
def _team_player_values(team):
    """Map of player -> (basic value, advanced value) from the team's latest scraped season."""
    values = {}
    for player, ppg, rpg, apg, spg, bpg, vorp, ws in get_latest_player_season_stats(team):
        basic = get_player_value(ppg, rpg, apg, spg, bpg) if None not in (ppg, rpg, apg, spg, bpg) else None
        advanced = (vorp * ws) if vorp is not None and ws is not None else None
        values[player] = (basic, advanced)
    return values


def get_injury_value(injured_players, team):
    """Team's total player value minus injured players' value, from stored season stats."""
    values = _team_player_values(team)
    total_value = sum(basic for basic, _ in values.values() if basic is not None)
    injury_value = sum(
        values[player][0] for player in (injured_players or [])
        if player in values and values[player][0] is not None
    )
    return total_value - injury_value


def get_injury_advanced(injured_players, team):
    """Team's total advanced value (vorp*ws) minus injured players', from stored season stats."""
    values = _team_player_values(team)
    total_advanced = sum(advanced for _, advanced in values.values() if advanced is not None)
    injury_advanced = sum(
        values[player][1] for player in (injured_players or [])
        if player in values and values[player][1] is not None
    )
    return total_advanced - injury_advanced


def get_current_team_injuries(team):
    """Current live injury report for a team (from the DB, refreshed by pipeline/scrape_teams.py)."""
    return get_current_injuries(team)


