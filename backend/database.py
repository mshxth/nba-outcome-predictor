"""SQLite database functions for NBA predictor."""

import sqlite3
from pathlib import Path

DB_PATH = 'data/nba_data.db'


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
    
    # Create indexes for faster queries
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_games_date ON games(date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_games_teams ON games(home_team, away_team)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_team_stats_team ON team_stats(team)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_team_stats_game ON team_stats(game_id)')
    
    conn.commit()
    conn.close()
    print(f"Database created at {DB_PATH}")


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


def get_all_dates_for_team(team):
    """Get all dates where team played."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT DISTINCT g.date
        FROM team_stats ts
        JOIN games g ON ts.game_id = g.id
        WHERE ts.team = ?
        ORDER BY g.date
    ''', (team,))
    
    results = [row[0] for row in cursor.fetchall()]
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