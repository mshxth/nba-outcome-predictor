"""Pure HTML-parsing functions for basketball-reference pages.

These take an already-fetched HTML string and return structured data --
no network calls, no file I/O. Fetching/caching lives in the scrape_*.py
scripts; DB writes live in backend/database.py.
"""

from bs4 import BeautifulSoup, Comment


def parse_four_factors(html):
    """Parse the four-factors table (off_rtg, efg_pct, tov_pct, orb_pct) from a box score page.

    Returns {'home': {metric: value, ...}, 'away': {metric: value, ...}} or None if not found.
    """
    soup = BeautifulSoup(html, 'html.parser')
    comments = soup.find_all(string=lambda text: isinstance(text, Comment))

    metrics = ['off_rtg', 'efg_pct', 'tov_pct', 'orb_pct']

    for comment in comments:
        comment_soup = BeautifulSoup(comment, 'html.parser')
        div_four_factors = comment_soup.find('div', id='div_four_factors')
        if div_four_factors:
            rows = div_four_factors.find('tbody').find_all('tr')
            away_row, home_row = rows[0], rows[1]
            away = {m: float(away_row.find('td', attrs={'data-stat': m}).get_text()) for m in metrics}
            home = {m: float(home_row.find('td', attrs={'data-stat': m}).get_text()) for m in metrics}
            return {'home': home, 'away': away}

    return None


def parse_final_score(html):
    """Parse the final score from a box score page. Returns (home_score, away_score, home_win)."""
    soup = BeautifulSoup(html, 'html.parser')
    scores = soup.find('div', class_='scorebox').find_all('div', class_='scores')

    away_score = float(scores[0].find('div', class_='score').get_text())
    home_score = float(scores[1].find('div', class_='score').get_text())
    home_win = 1 if home_score > away_score else 0

    return home_score, away_score, home_win


def parse_inactive_players(html):
    """Parse the "Inactive:" line from a box score page, attributed per team abbreviation.

    Returns {team_abbr: [player_name, ...]}. The original scraper only used
    soup.find() (singular) here, which silently merged both teams' inactive
    players into one undifferentiated list -- this walks the same div but
    tracks which team-abbreviation marker each player follows, so each name
    ends up attributed to the correct team.
    """
    soup = BeautifulSoup(html, 'html.parser')
    strong_tag = soup.find('strong', string=lambda s: s and 'Inactive' in s)
    if not strong_tag:
        return {}

    container = strong_tag.find_parent('div')
    inactives = {}
    current_abbr = None

    for el in container.find_all(['span', 'a']):
        if el.name == 'span':
            abbr_strong = el.find('strong')
            if abbr_strong:
                current_abbr = abbr_strong.get_text(strip=True)
                inactives.setdefault(current_abbr, [])
        elif el.name == 'a' and current_abbr:
            inactives[current_abbr].append(el.get_text(strip=True))

    return inactives


def parse_team_roster(html):
    """Parse a team page's roster. Returns a list of player names."""
    soup = BeautifulSoup(html, "html.parser")

    roster = []
    roster_data = soup.find('div', id='div_roster').find_all('tr')
    for player_data in roster_data:
        player = player_data.find('td', attrs={'data-stat': 'player'})
        if player:
            roster.append(player.find_all('a')[0].get_text())

    return roster


def parse_team_per_game_stats(html):
    """Parse a team page's per-game stats table.

    Returns {player_name: {'ppg':.., 'rpg':.., 'apg':.., 'spg':.., 'bpg':..}}.
    """
    soup = BeautifulSoup(html, "html.parser")
    players = soup.find('table', id='per_game_stats').find('tbody').find_all('tr')

    stats = {}
    for player in players:
        name_cell = player.find('td', attrs={'data-stat': 'name_display'})
        if not name_cell or not name_cell.find('a'):
            continue
        name = name_cell.find('a').get_text()
        stats[name] = {
            'ppg': float(player.find('td', attrs={'data-stat': 'pts_per_g'}).get_text()),
            'rpg': float(player.find('td', attrs={'data-stat': 'trb_per_g'}).get_text()),
            'apg': float(player.find('td', attrs={'data-stat': 'ast_per_g'}).get_text()),
            'spg': float(player.find('td', attrs={'data-stat': 'stl_per_g'}).get_text()),
            'bpg': float(player.find('td', attrs={'data-stat': 'blk_per_g'}).get_text()),
        }

    return stats


def parse_team_advanced_stats(html):
    """Parse a team page's advanced stats table (VORP, WS), hidden in an HTML comment.

    Returns {player_name: {'vorp':.., 'ws':..}}.
    """
    soup = BeautifulSoup(html, "html.parser")
    comments = soup.find_all(string=lambda text: isinstance(text, Comment))

    for comment in comments:
        comment_soup = BeautifulSoup(comment, 'html.parser')
        advanced = comment_soup.find('table', id='advanced')
        if advanced:
            rows = advanced.find('tbody').find_all('tr')
            stats = {}
            for player in rows:
                name_cell = player.find('td', attrs={'data-stat': 'name_display'})
                if not name_cell or not name_cell.find('a'):
                    continue
                name = name_cell.find('a').get_text()
                stats[name] = {
                    'vorp': float(player.find('td', attrs={'data-stat': 'vorp'}).get_text()),
                    'ws': float(player.find('td', attrs={'data-stat': 'ws'}).get_text()),
                }
            return stats

    return {}


def parse_team_injuries(html):
    """Parse a team page's current injury report, hidden in an HTML comment.

    Returns a list of player names.
    """
    soup = BeautifulSoup(html, "html.parser")
    comments = soup.find_all(string=lambda text: isinstance(text, Comment))

    for comment in comments:
        comment_soup = BeautifulSoup(comment, 'html.parser')
        div_injuries = comment_soup.find('div', class_='table_container', id='div_injuries')
        if div_injuries:
            links = div_injuries.find('tbody').find_all('a')
            # Each row has 2 links (player name + team); only the even-indexed ones are player names.
            return [link.get_text() for i, link in enumerate(links) if i % 2 == 0]

    return []
