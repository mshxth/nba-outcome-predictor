"""SQLite database functions for NBA predictor."""

import os
import sqlite3
from pathlib import Path

# NBA_DB_PATH points offline evaluation at a larger database kept outside the repo
DB_PATH = os.environ.get('NBA_DB_PATH') or str(Path(__file__).resolve().parent / 'data' / 'nba_data.db')


def create_database():
    """Create database schema."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Games table - stores basic game info
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            home_score REAL,
            away_score REAL,
            home_win INTEGER,
            UNIQUE(date, home_team, away_team)
        )
    ''')
    
    # Team stats table - stores four factors stats
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS team_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER NOT NULL,
            team TEXT NOT NULL,
            is_home INTEGER NOT NULL,
            off_rtg REAL,
            opp_off_rtg REAL,
            efg_pct REAL,
            opp_efg_pct REAL,
            tov_pct REAL,
            opp_tov_pct REAL,
            orb_pct REAL,
            opp_orb_pct REAL,
            FOREIGN KEY (game_id) REFERENCES games(id)
        )
    ''')
    
    # Game injuries table - accurate per-game inactive player lists (from box score "Inactive:" list)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS game_injuries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER NOT NULL,
            team TEXT NOT NULL,
            player TEXT NOT NULL,
            FOREIGN KEY (game_id) REFERENCES games(id)
        )
    ''')

    # Current injuries table - live injury report per team, refreshed by the scheduled scraper
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS current_injuries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team TEXT NOT NULL,
            player TEXT NOT NULL,
            scraped_at TEXT NOT NULL
        )
    ''')

    # Player game stats table - full per-player basic + advanced box score line for
    # every player who recorded minutes in a game (not just season aggregates)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS player_game_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER NOT NULL,
            team TEXT NOT NULL,
            player TEXT NOT NULL,
            minutes REAL,
            fg REAL, fga REAL, fg_pct REAL,
            fg3 REAL, fg3a REAL, fg3_pct REAL,
            ft REAL, fta REAL, ft_pct REAL,
            orb REAL, drb REAL, trb REAL,
            ast REAL, stl REAL, blk REAL, tov REAL, pf REAL, pts REAL,
            game_score REAL, plus_minus REAL,
            ts_pct REAL, efg_pct REAL,
            fg3a_per_fga_pct REAL, fta_per_fga_pct REAL,
            orb_pct REAL, drb_pct REAL, trb_pct REAL,
            ast_pct REAL, stl_pct REAL, blk_pct REAL, tov_pct REAL,
            usg_pct REAL, off_rtg REAL, def_rtg REAL, bpm REAL,
            FOREIGN KEY (game_id) REFERENCES games(id),
            UNIQUE(game_id, team, player)
        )
    ''')

    # Create indexes for faster queries
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_games_date ON games(date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_games_teams ON games(home_team, away_team)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_player_game_stats_game ON player_game_stats(game_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_team_stats_team ON team_stats(team)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_team_stats_game ON team_stats(game_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_game_injuries_team ON game_injuries(team)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_current_injuries_team ON current_injuries(team)')

    conn.commit()
    conn.close()
    print(f"Database created at {DB_PATH}")


# ===== WRITE FUNCTIONS (used by pipeline/ scraper and backfill scripts) =====

def game_exists(date, home_team, away_team):
    """Check if a game is already stored (idempotency check for scrapers)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT 1 FROM games WHERE date = ? AND home_team = ? AND away_team = ?
    ''', (date, home_team, away_team))

    result = cursor.fetchone()
    conn.close()
    return result is not None


def insert_game(date, home_team, away_team, home_score, away_score, home_win):
    """Insert a game (idempotent via UNIQUE constraint) and return its id."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        INSERT OR IGNORE INTO games (date, home_team, away_team, home_score, away_score, home_win)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (date, home_team, away_team, home_score, away_score, home_win))

    cursor.execute('''
        SELECT id FROM games WHERE date = ? AND home_team = ? AND away_team = ?
    ''', (date, home_team, away_team))
    game_id = cursor.fetchone()[0]

    conn.commit()
    conn.close()
    return game_id


def insert_team_stats(game_id, team, is_home, off_rtg, opp_off_rtg, efg_pct, opp_efg_pct,
                       tov_pct, opp_tov_pct, orb_pct, opp_orb_pct):
    """Insert a team's four-factors stats for a game."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO team_stats (
            game_id, team, is_home, off_rtg, opp_off_rtg, efg_pct, opp_efg_pct,
            tov_pct, opp_tov_pct, orb_pct, opp_orb_pct
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (game_id, team, is_home, off_rtg, opp_off_rtg, efg_pct, opp_efg_pct,
          tov_pct, opp_tov_pct, orb_pct, opp_orb_pct))

    conn.commit()
    conn.close()


def insert_game_injuries(game_id, team, players):
    """Insert the inactive-player list for a team in a game."""
    if not players:
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.executemany('''
        INSERT INTO game_injuries (game_id, team, player) VALUES (?, ?, ?)
    ''', [(game_id, team, player) for player in players])

    conn.commit()
    conn.close()


def insert_player_game_stats(game_id, team, player, stats):
    """Insert a player's per-game box score line (idempotent via UNIQUE constraint).

    `stats` is a dict keyed by the same column names as the `player_game_stats`
    table (minutes, fg, fga, ..., off_rtg, def_rtg, bpm) -- see
    pipeline/parsers.py:parse_player_game_stats.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    columns = [
        'minutes', 'fg', 'fga', 'fg_pct', 'fg3', 'fg3a', 'fg3_pct', 'ft', 'fta', 'ft_pct',
        'orb', 'drb', 'trb', 'ast', 'stl', 'blk', 'tov', 'pf', 'pts', 'game_score', 'plus_minus',
        'ts_pct', 'efg_pct', 'fg3a_per_fga_pct', 'fta_per_fga_pct', 'orb_pct', 'drb_pct', 'trb_pct',
        'ast_pct', 'stl_pct', 'blk_pct', 'tov_pct', 'usg_pct', 'off_rtg', 'def_rtg', 'bpm',
    ]
    placeholders = ', '.join('?' * (len(columns) + 3))
    cursor.execute(f'''
        INSERT OR IGNORE INTO player_game_stats (game_id, team, player, {', '.join(columns)})
        VALUES ({placeholders})
    ''', (game_id, team, player, *[stats.get(c) for c in columns]))

    conn.commit()
    conn.close()


def player_game_stats_exist(game_id):
    """Check whether a game already has per-player stats stored (backfill resume check)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('SELECT 1 FROM player_game_stats WHERE game_id = ? LIMIT 1', (game_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None


def get_game_injuries(game_id, team):
    """Get the inactive-player list for a team in a specific game."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('SELECT player FROM game_injuries WHERE game_id = ? AND team = ?', (game_id, team))
    results = [row[0] for row in cursor.fetchall()]
    conn.close()
    return results


def replace_current_injuries(team, players, scraped_at):
    """Replace a team's current injury report with a fresh list."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('DELETE FROM current_injuries WHERE team = ?', (team,))
    if players:
        cursor.executemany('''
            INSERT INTO current_injuries (team, player, scraped_at) VALUES (?, ?, ?)
        ''', [(team, player, scraped_at) for player in players])

    conn.commit()
    conn.close()


def get_current_injuries(team):
    """Get a team's current injury report."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('SELECT player FROM current_injuries WHERE team = ?', (team,))
    results = [row[0] for row in cursor.fetchall()]
    conn.close()
    return results


# ===== READ FUNCTIONS =====

def get_team_stats_for_dates(team, dates, metric_name):
    """Get team stats for specific dates and metric."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Map metric names to column names
    metric_map = {
        'off_rtg': ('off_rtg', 'opp_off_rtg'),
        'efg_pct': ('efg_pct', 'opp_efg_pct'),
        'tov_pct': ('tov_pct', 'opp_tov_pct'),
        'orb_pct': ('orb_pct', 'opp_orb_pct')
    }
    
    if metric_name not in metric_map:
        return []
    
    team_col, opp_col = metric_map[metric_name]
    
    # Build query with date list
    placeholders = ','.join('?' * len(dates))
    query = f'''
        SELECT g.date, ts.{team_col}, ts.{opp_col}
        FROM team_stats ts
        JOIN games g ON ts.game_id = g.id
        WHERE ts.team = ? AND g.date IN ({placeholders})
        ORDER BY g.date
    '''
    
    cursor.execute(query, [team] + dates)
    results = cursor.fetchall()
    conn.close()
    
    # Convert to dict format like original get_metrics
    metrics = []
    date_dict = {date: None for date in dates}
    
    for date, team_val, opp_val in results:
        date_dict[date] = [team_val, opp_val]
    
    # Return in order of input dates
    for date in dates:
        metrics.append(date_dict[date])

    return metrics


def get_team_player_stats_for_dates(team, dates):
    """Get every player's per-game (minutes, pts, trb, ast, stl, blk, bpm) line for a team across specific dates."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    placeholders = ','.join('?' * len(dates))
    cursor.execute(f'''
        SELECT p.player, p.minutes, p.pts, p.trb, p.ast, p.stl, p.blk, p.bpm
        FROM player_game_stats p
        JOIN games g ON p.game_id = g.id
        WHERE p.team = ? AND g.date IN ({placeholders})
    ''', [team] + dates)

    results = cursor.fetchall()
    conn.close()
    return results


def get_team_player_stats_for_season(team, season_start_date, before_date):
    """Get every player's per-game (minutes, pts, trb, ast, stl, blk, bpm) line for a team,
    for every game from season_start_date up to (not including) before_date."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT p.player, p.minutes, p.pts, p.trb, p.ast, p.stl, p.blk, p.bpm
        FROM player_game_stats p
        JOIN games g ON p.game_id = g.id
        WHERE p.team = ? AND g.date >= ? AND g.date < ?
    ''', (team, season_start_date, before_date))

    results = cursor.fetchall()
    conn.close()
    return results


def get_home_win(date, home, away):
    """Get if home team won."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT home_win
        FROM games
        WHERE date = ? AND home_team = ? AND away_team = ?
    ''', (date, home, away))
    
    result = cursor.fetchone()
    conn.close()
    
    return result[0] if result else None


def check_back_to_back(date, team):
    """Check if team played previous day."""
    from datetime import datetime, timedelta
    
    date_obj = datetime.strptime(date, "%Y-%m-%d")
    previous_date = (date_obj - timedelta(days=1)).strftime("%Y-%m-%d")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT COUNT(*)
        FROM team_stats ts
        JOIN games g ON ts.game_id = g.id
        WHERE ts.team = ? AND g.date = ?
    ''', (team, previous_date))
    
    result = cursor.fetchone()
    conn.close()
    
    return 1 if result[0] > 0 else 0


if __name__ == "__main__":
    create_database()