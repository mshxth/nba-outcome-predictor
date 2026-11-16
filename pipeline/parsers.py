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
            name = el.get_text(strip=True)
            # basketball-reference sometimes links an inactive player to a
            # placeholder "tmp-<id>" page (e.g. a recent two-way/G-League
            # call-up without a full player page yet) with no link text.
            if name:
                inactives[current_abbr].append(name)

    return inactives


_BASIC_BOX_STAT_KEYS = [
    'fg', 'fga', 'fg_pct', 'fg3', 'fg3a', 'fg3_pct', 'ft', 'fta', 'ft_pct',
    'orb', 'drb', 'trb', 'ast', 'stl', 'blk', 'tov', 'pf', 'pts', 'game_score', 'plus_minus',
]
_ADVANCED_BOX_STAT_KEYS = [
    'ts_pct', 'efg_pct', 'fg3a_per_fga_pct', 'fta_per_fga_pct', 'orb_pct', 'drb_pct', 'trb_pct',
    'ast_pct', 'stl_pct', 'blk_pct', 'tov_pct', 'usg_pct', 'off_rtg', 'def_rtg', 'bpm',
]


def _parse_box_table(html, table_id, stat_keys):
    """Parse one team's basic or advanced per-player box score table.

    Returns {player_name: {'minutes': float or None, key: float or None, ...}}.
    Skips the mid-table "Reserves" separator row (no player link) and DNP rows
    (a `data-stat="reason"` cell instead of real stats) -- neither has a stat line to store.
    """
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table', id=table_id)
    if table is None:
        return {}

    players = {}
    for row in table.find('tbody').find_all('tr'):
        player_cell = row.find('th', attrs={'data-stat': 'player'})
        if not player_cell or not player_cell.find('a'):
            continue
        if row.find('td', attrs={'data-stat': 'reason'}):
            continue
        player = player_cell.find('a').get_text(strip=True)

        mp_cell = row.find('td', attrs={'data-stat': 'mp'})
        mp_text = mp_cell.get_text(strip=True) if mp_cell else ''
        minutes = None
        if ':' in mp_text:
            mins, secs = mp_text.split(':')
            minutes = int(mins) + int(secs) / 60

        stats = {'minutes': minutes}
        for key in stat_keys:
            cell = row.find('td', attrs={'data-stat': key})
            text = cell.get_text(strip=True) if cell else ''
            stats[key] = float(text) if text else None
        players[player] = stats

    return players


def parse_player_game_stats(html, home_abbr, away_abbr):
    """Parse both teams' full per-player basic + advanced box score lines from a box score page.

    Returns {'home': [{'player': .., 'minutes': .., ...all stat keys}, ...], 'away': [...]}.
    Only includes players who actually recorded minutes (DNPs are skipped -- the
    pregame inactive list is separately and correctly tracked via parse_inactive_players).
    """
    result = {}
    for side, abbr in (('home', home_abbr), ('away', away_abbr)):
        basic = _parse_box_table(html, f'box-{abbr}-game-basic', _BASIC_BOX_STAT_KEYS)
        advanced = _parse_box_table(html, f'box-{abbr}-game-advanced', _ADVANCED_BOX_STAT_KEYS)

        rows = []
        for player, stats in basic.items():
            row = {'player': player, **stats}
            adv = dict(advanced.get(player, {}))
            adv.pop('minutes', None)  # duplicate of basic table's minutes
            row.update(adv)
            rows.append(row)
        result[side] = rows

    return result


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
