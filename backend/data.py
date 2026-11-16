"""Data functions using SQLite database instead of HTML parsing."""

from datetime import datetime, timedelta
from functools import lru_cache
from config import get_last_n_days_from_date, get_season_start_date
from database import (
    get_team_stats_for_dates, get_home_win, check_back_to_back,
    get_team_player_stats_for_dates, get_team_player_stats_for_season,
    get_current_injuries, get_game_injuries,
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


def get_input_format(date, home, away, func, windows=(7, 30)):
    """Helper function to get proper format for input.

    For each window size (days), blends each team's own rolling average with
    the opponent's rolling "allowed" average, then averages the result across
    all given window sizes. Defaults to (7, 30) to match live serving; pass a
    different set of windows (e.g. just (15,) or (7, 15, 30)) to experiment
    with how much history the model should look back over.
    """
    home_vals = []
    away_vals = []
    for window in windows:
        dates = get_last_n_days_from_date(date, window)
        home_avgs = func(dates, home)
        away_avgs = func(dates, away)
        home_vals.append((home_avgs[0] + away_avgs[1]) / 2)
        away_vals.append((away_avgs[0] + home_avgs[1]) / 2)

    return sum(home_vals) / len(home_vals), sum(away_vals) / len(away_vals)


# ===== INJURY/PLAYER-VALUE FUNCTIONS (DB-backed, replaces HTML parsing at request time) =====

def get_player_value(ppg, rpg, apg, spg, bpg):
    """Calculate player value from stats."""
    return ppg + (1.2 * rpg) + (1.5 * apg) + (2 * spg) + (2 * bpg)


# Garbage-time appearances (a few seconds of court time) produce degenerate rate
# stats -- e.g. usg_pct=100 or bpm=+/-1000 for a single-possession cameo -- that
# are pure noise, not signal, about a player's real value. Excluded from every
# player-value aggregation below.
MIN_MINUTES_GARBAGE_TIME = 3.0


def _aggregate_player_values(rows, min_minutes=MIN_MINUTES_GARBAGE_TIME):
    """Aggregate (player, minutes, pts, trb, ast, stl, blk, bpm) rows into
    {player: (basic value, advanced value)}, dropping garbage-time appearances.

    Basic value is get_player_value() over each player's average pts/trb/ast/stl/blk
    across the given rows. Advanced value is average BPM (Box Plus-Minus) -- the
    per-game stat VORP is itself derived from, since VORP/Win Shares are
    season-cumulative and have no per-game equivalent.
    """
    by_player = {}
    for player, minutes, pts, trb, ast, stl, blk, bpm in rows:
        if minutes is None or minutes < min_minutes:
            continue
        by_player.setdefault(player, {'pts': [], 'trb': [], 'ast': [], 'stl': [], 'blk': [], 'bpm': []})
        for key, val in (('pts', pts), ('trb', trb), ('ast', ast), ('stl', stl), ('blk', blk), ('bpm', bpm)):
            if val is not None:
                by_player[player][key].append(val)

    values = {}
    for player, stats in by_player.items():
        basic = advanced = None
        if stats['pts']:
            avg = {k: sum(v) / len(v) if v else 0 for k, v in stats.items()}
            basic = get_player_value(avg['pts'], avg['trb'], avg['ast'], avg['stl'], avg['blk'])
        if stats['bpm']:
            advanced = sum(stats['bpm']) / len(stats['bpm'])
        values[player] = (basic, advanced)
    return values


@lru_cache(maxsize=256)
def _team_rolling_player_values(team, date, windows=(7, 30)):
    """Map of player -> (basic value, advanced value) from rolling pre-game per-game stats,
    blended across window sizes exactly like the four-factor rolling stats in
    get_input_format -- automatically point-in-time correct for any historical date.
    """
    basic_by_window = []
    advanced_by_window = []

    for window in windows:
        dates = get_last_n_days_from_date(date, window)
        rows = get_team_player_stats_for_dates(team, dates)
        window_values = _aggregate_player_values(rows)
        basic_by_window.append({p: v[0] for p, v in window_values.items() if v[0] is not None})
        advanced_by_window.append({p: v[1] for p, v in window_values.items() if v[1] is not None})

    all_players = set().union(*basic_by_window, *advanced_by_window)
    values = {}
    for player in all_players:
        basics = [d[player] for d in basic_by_window if player in d]
        advanceds = [d[player] for d in advanced_by_window if player in d]
        values[player] = (
            sum(basics) / len(basics) if basics else None,
            sum(advanceds) / len(advanceds) if advanceds else None,
        )
    return values


@lru_cache(maxsize=256)
def _team_season_player_values(team, date):
    """Map of player -> (basic value, advanced value) from season-to-date per-game stats
    (season start through the day before `date`) instead of a rolling window -- tests
    whether a season-long average, smoother/less noisy than the 7/30-day rolling blend,
    makes for a better injury-impact signal.
    """
    season_start = get_season_start_date(date)
    rows = get_team_player_stats_for_season(team, season_start, date)
    return _aggregate_player_values(rows)


def _value_delta(values, injured_players, idx):
    """Team's total value (basic if idx=0, advanced if idx=1) minus injured players' value."""
    total = sum(v[idx] for v in values.values() if v[idx] is not None)
    injured = sum(
        values[player][idx] for player in (injured_players or [])
        if player in values and values[player][idx] is not None
    )
    return total - injured


def get_injury_value(injured_players, team, date, windows=(7, 30)):
    """Team's total rolling player value minus injured players' value."""
    return _value_delta(_team_rolling_player_values(team, date, windows), injured_players, 0)


def get_injury_advanced(injured_players, team, date, windows=(7, 30)):
    """Team's total rolling advanced value (avg BPM) minus injured players'."""
    return _value_delta(_team_rolling_player_values(team, date, windows), injured_players, 1)


def get_injury_value_season(injured_players, team, date):
    """Team's total season-to-date player value minus injured players' value."""
    return _value_delta(_team_season_player_values(team, date), injured_players, 0)


def get_injury_advanced_season(injured_players, team, date):
    """Team's total season-to-date advanced value (avg BPM) minus injured players'."""
    return _value_delta(_team_season_player_values(team, date), injured_players, 1)


def get_current_team_injuries(team):
    """Current live injury report for a team (from the DB, refreshed by pipeline/scrape_teams.py)."""
    return get_current_injuries(team)


