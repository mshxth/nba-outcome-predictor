"""Data functions using SQLite database instead of HTML parsing."""

from datetime import datetime, timedelta
from pathlib import Path
from bs4 import BeautifulSoup, Comment
from config import TEAM_TO_ABBR, get_last_30_days_from_date, get_last_7_days_from_date
from database import get_team_stats_for_dates, get_home_win, check_back_to_back


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


# ===== FUNCTIONS THAT STILL USE HTML (for injuries) =====

def scrape_team_roster(team):
    """Get team roster from HTML."""
    file = f"TEAMS/{TEAM_TO_ABBR[team]}.html"

    with open(file) as f:
        page = f.read()
        
    soup = BeautifulSoup(page, "html.parser")

    roster = []
    roster_data = soup.find('div', id='div_roster').find_all('tr')
    for player_data in roster_data:
        player = player_data.find('td', attrs={'data-stat': 'player'})
        if player:
            roster.append(player.find_all('a')[0].get_text())
    
    return roster


def scrape_team_injuries(team):
    """Get team injuries from HTML."""
    file = f"TEAMS/{TEAM_TO_ABBR[team]}.html"
    
    with open(file) as f:
        page = f.read()
    
    soup = BeautifulSoup(page, "html.parser")
   
    comments = soup.find_all(string=lambda text: isinstance(text, Comment))
    
    for comment in comments:
        comment_soup = BeautifulSoup(comment, 'html.parser')  
        div_injuries = comment_soup.find('div', class_='table_container', id='div_injuries')
        if div_injuries:
            injuries = div_injuries.find('tbody').find_all('a')
            count = -1
            reserves = []
            for injury in injuries:
                count += 1
                if injury and count % 2 == 0:
                    reserves.append(injury.get_text())
            return reserves


def scrape_injuries_from_date(date, home, away):
    """Get injuries from date - from HTML."""
    file = f"GAMES/{date}-{home}-{away}.html"

    with open(file) as f:
        page = f.read()

    soup = BeautifulSoup(page, "html.parser")
    inactives = soup.find('strong', text='Inactive:\xa0').find_parent('div').find_all('a')
    injuries = []
    for inactive in inactives:
        injuries.append(inactive.get_text())
    
    return injuries


def get_player_value(ppg, rpg, apg, spg, bpg):
    """Calculate player value from stats."""
    return ppg + (1.2 * rpg) + (1.5 * apg) + (2 * spg) + (2 * bpg)


def scrape_team_value(team):
    """Get total team value from stats."""
    file = f"TEAMS/{TEAM_TO_ABBR[team]}.html"
    
    with open(file) as f:
        page = f.read()

    soup = BeautifulSoup(page, "html.parser")
    players = soup.find('table', id='per_game_stats').find('tbody').find_all('tr')

    total = 0

    for player in players:
        ppg = float(player.find('td', attrs={'data-stat': 'pts_per_g'}).get_text())
        rpg = float(player.find('td', attrs={'data-stat': 'trb_per_g'}).get_text())
        apg = float(player.find('td', attrs={'data-stat': 'ast_per_g'}).get_text())
        spg = float(player.find('td', attrs={'data-stat': 'stl_per_g'}).get_text())
        bpg = float(player.find('td', attrs={'data-stat': 'blk_per_g'}).get_text())
        total += get_player_value(ppg, rpg, apg, spg, bpg)
        
    return total


def scrape_player_value(team, player_name):
    """Get individual player value from stats."""
    file = f"TEAMS/{TEAM_TO_ABBR[team]}.html"
    
    with open(file) as f:
        page = f.read()

    soup = BeautifulSoup(page, "html.parser")
    players = soup.find('table', id='per_game_stats').find('tbody').find_all('tr')

    for player in players:
        name = player.find('td', attrs={'data-stat': 'name_display'}).find('a').get_text()
        if name == player_name: 
            ppg = float(player.find('td', attrs={'data-stat': 'pts_per_g'}).get_text())
            rpg = float(player.find('td', attrs={'data-stat': 'trb_per_g'}).get_text())
            apg = float(player.find('td', attrs={'data-stat': 'ast_per_g'}).get_text())
            spg = float(player.find('td', attrs={'data-stat': 'stl_per_g'}).get_text())
            bpg = float(player.find('td', attrs={'data-stat': 'blk_per_g'}).get_text())
            value = get_player_value(ppg, rpg, apg, spg, bpg)
            return value


def get_injury_value(injuries, team):
    """Calculate injury impact using player value."""
    injury_value = 0
    total_value = scrape_team_value(team)
    if injuries:
        for injury in injuries:
            player_value = scrape_player_value(team, injury)
            if player_value:
                injury_value += player_value
    
    return (total_value - injury_value)


def scrape_team_advanced(team):
    """Get team advanced stats."""
    file = f"TEAMS/{TEAM_TO_ABBR[team]}.html"

    with open(file) as f:
        page = f.read()
    
    soup = BeautifulSoup(page, "html.parser")

    comments = soup.find_all(string=lambda text: isinstance(text, Comment))
    
    for comment in comments:
        comment_soup = BeautifulSoup(comment, 'html.parser')  
        advanced = comment_soup.find('table', id='advanced')
        if advanced:
            advanced = advanced.find('tbody').find_all('tr')
            total = 0
            for player in advanced:
                vorp = float(player.find('td', attrs={'data-stat': 'vorp'}).get_text())
                ws = float(player.find('td', attrs={'data-stat': 'ws'}).get_text())
                total += (vorp * ws)

            return total


def scrape_player_advanced(team, player_name):
    """Get player advanced stats."""
    file = f"TEAMS/{TEAM_TO_ABBR[team]}.html"

    with open(file) as f:
        page = f.read()
    
    soup = BeautifulSoup(page, "html.parser")

    comments = soup.find_all(string=lambda text: isinstance(text, Comment))
    
    for comment in comments:
        comment_soup = BeautifulSoup(comment, 'html.parser')  
        advanced = comment_soup.find('table', id='advanced')
        if advanced:
            advanced = advanced.find('tbody').find_all('tr')
            for player in advanced:
                name = player.find('td', attrs={'data-stat': 'name_display'}).find('a').get_text()
                if name == player_name:
                    vorp = float(player.find('td', attrs={'data-stat': 'vorp'}).get_text())
                    ws = float(player.find('td', attrs={'data-stat': 'ws'}).get_text())
                    return vorp * ws


def get_injury_advanced(injuries, team):
    """Calculate injury impact using advanced analytics."""
    injury_advanced = 0
    total_advanced = scrape_team_advanced(team)
    if injuries:
        for injury in injuries:
            player_advanced = scrape_player_advanced(team, injury)
            if player_advanced:
                injury_advanced += player_advanced
    
    return (total_advanced - injury_advanced)


# ===== FOR TRAINING: Still need to parse game HTML for actual stats =====

def scrape_team_metrics_from_game(date, home, away, metric_name):
    """Extract metric from game HTML - used for training data."""
    file = f"GAMES/{date}-{home}-{away}.html"

    with open(file) as f:
        page = f.read()

    soup = BeautifulSoup(page, 'html.parser')
    comments = soup.find_all(string=lambda text: isinstance(text, Comment))

    for comment in comments:
        comment_soup = BeautifulSoup(comment, 'html.parser')
        div_four_factors = comment_soup.find('div', id='div_four_factors')
        if div_four_factors:
            away_or = float(div_four_factors.find('tbody').find_all('tr')[0].find('td', attrs={'data-stat': metric_name}).get_text())
            home_or = float(div_four_factors.find('tbody').find_all('tr')[1].find('td', attrs={'data-stat': metric_name}).get_text())
            return [home_or, away_or]