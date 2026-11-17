"""Copy per-player box score lines from another database into the target database.

Games are matched on (date, home_team, away_team), so the two databases can have
different game ids. Only the columns the injury features use are copied. Safe to
re-run: rows already present are skipped (UNIQUE game_id/team/player).

Usage:
    NBA_DB_PATH=path/to/target.db python3 pipeline/copy_player_stats.py path/to/source.db
"""

import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / 'backend'))

import database


def main(source_path):
    database.create_database()
    cols = ', '.join(database.PLAYER_GAME_COLUMNS)
    conn = sqlite3.connect(database.DB_PATH)
    conn.execute('ATTACH DATABASE ? AS src', (str(source_path),))
    before = conn.execute('SELECT COUNT(*) FROM player_game_stats').fetchone()[0]
    conn.execute(f'''
        INSERT OR IGNORE INTO main.player_game_stats (game_id, team, player, {cols})
        SELECT t.id, p.team, p.player, {', '.join('p.' + c for c in database.PLAYER_GAME_COLUMNS)}
        FROM src.player_game_stats p
        JOIN src.games s ON s.id = p.game_id
        JOIN main.games t ON t.date = s.date AND t.home_team = s.home_team AND t.away_team = s.away_team
    ''')
    conn.commit()
    after = conn.execute('SELECT COUNT(*) FROM player_game_stats').fetchone()[0]
    games = conn.execute('SELECT COUNT(DISTINCT game_id) FROM player_game_stats').fetchone()[0]
    total = conn.execute('SELECT COUNT(*) FROM games').fetchone()[0]
    print(f'Copied {after - before} rows. {games} of {total} games now have player stats.')
    conn.close()


if __name__ == '__main__':
    main(sys.argv[1])
