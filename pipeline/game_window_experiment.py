"""Experiment: rolling windows measured in GAMES (e.g. last 3 and 15) instead of DAYS (7 and 30).

A 7-day window holds anywhere from 1 to 4 games, so the old features averaged over a
different amount of data from game to game. Here every feature uses exactly the last N
games a team played before the game date (carrying over from the previous season at the
start of a season, like the day-based version's fallback did).

Blend is the same as pipeline/../backend/data.py:get_input_format: for each window, the
home value is (home team's own average + away team's "allowed" average) / 2, and the
final feature averages across the windows.

Usage:
    NBA_DB_PATH=~/nba-data/nba_data_full.db python3 pipeline/game_window_experiment.py
"""

import sqlite3
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings('ignore')
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / 'backend'))
sys.path.insert(0, str(REPO_ROOT / 'pipeline'))

import database
import model_comparison as mc

METRICS = {'ORtg': ('off_rtg', 'opp_off_rtg'), 'eFG%': ('efg_pct', 'opp_efg_pct'),
           'TOV%': ('tov_pct', 'opp_tov_pct'), 'ORB%': ('orb_pct', 'opp_orb_pct')}


def team_game_table():
    conn = sqlite3.connect(database.DB_PATH)
    df = pd.read_sql_query('''
        SELECT g.id AS game_id, g.date, t.team, t.off_rtg, t.opp_off_rtg, t.efg_pct, t.opp_efg_pct,
               t.tov_pct, t.opp_tov_pct, t.orb_pct, t.opp_orb_pct
        FROM team_stats t JOIN games g ON g.id = t.game_id
    ''', conn)
    conn.close()
    return df.sort_values(['team', 'date', 'game_id']).reset_index(drop=True)


def rolling_prior(tg, n):
    """For every team-game: mean of each stat over the n games BEFORE it (NaN until n exist)."""
    out = tg[['game_id', 'team']].copy()
    for _, (own, opp) in METRICS.items():
        for col in (own, opp):
            out[col] = tg.groupby('team')[col].transform(lambda s: s.rolling(n, min_periods=n).mean().shift(1))
    return out


def build(df, windows):
    """Replace the 8 four-factor columns of the cached feature frame with game-window versions.

    Returns (new frame, dict of per-window home/away columns for 'separate' use).
    """
    tg = team_game_table()
    per_window = {}
    for n in windows:
        r = rolling_prior(tg, n)
        per_window[n] = r.set_index(['game_id', 'team'])
    out = df[['season', 'game_id', 'date', 'Home B2B', 'Away B2B', 'Home Win']].copy()
    games = database_games(df['game_id'])
    out = out.merge(games, on='game_id')
    cols = {}
    for label, (own, opp) in METRICS.items():
        for n in windows:
            r = per_window[n]
            h_own = r[own].reindex(list(zip(out.game_id, out.home_team))).to_numpy()
            h_opp = r[opp].reindex(list(zip(out.game_id, out.home_team))).to_numpy()
            a_own = r[own].reindex(list(zip(out.game_id, out.away_team))).to_numpy()
            a_opp = r[opp].reindex(list(zip(out.game_id, out.away_team))).to_numpy()
            cols[(label, n, 'Home')] = (h_own + a_opp) / 2
            cols[(label, n, 'Away')] = (a_own + h_opp) / 2
    return out, cols


def database_games(game_ids):
    conn = sqlite3.connect(database.DB_PATH)
    g = pd.read_sql_query('SELECT id AS game_id, home_team, away_team FROM games', conn)
    conn.close()
    return g[g.game_id.isin(set(game_ids))]


def blended_frame(df, windows):
    out, cols = build(df, windows)
    for label in METRICS:
        for side in ('Home', 'Away'):
            out[f'{side} {label}'] = np.mean([cols[(label, n, side)] for n in windows], axis=0)
    ok = out[[f'{s} {l}' for l in METRICS for s in ('Home', 'Away')]].notna().all(axis=1)
    return out[ok].reset_index(drop=True), int((~ok).sum())


def separate_frame(df, windows):
    out, cols = build(df, windows)
    names = []
    for label in METRICS:
        for n in windows:
            for side in ('Home', 'Away'):
                name = f'{side} {label} g{n}'
                out[name] = cols[(label, n, side)]
                names.append(name)
    ok = out[names].notna().all(axis=1)
    return out[ok].reset_index(drop=True), names, int((~ok).sum())
