"""ML model loading and prediction functions for API."""

import pickle
from datetime import datetime
from functools import lru_cache
from pathlib import Path

# Import from current directory (backend folder)
from config import TEAM_TO_ABBR, CURRENT_TEAMS
from data import (
    get_game_window_features,
    get_current_team_injuries, scrape_back_to_back, get_injury_value, get_injury_advanced
)
from database import get_game_id, get_game_injuries

# Paths - use local files
MODEL_PATH = str(Path(__file__).resolve().parent / 'models' / 'trained_model.pkl')

# Global cache for the loaded model (injuries/player stats now come straight from the
# DB, refreshed by pipeline/scrape_teams.py, so no separate request-time cache is needed)
_model_cache = None


def load_model():
    """Load the trained model from pickle file (cached)."""
    global _model_cache
    
    if _model_cache is not None:
        return _model_cache
    
    try:
        with open(MODEL_PATH, 'rb') as f:
            model_data = pickle.load(f)
        _model_cache = model_data
        return model_data
    except FileNotFoundError:
        raise Exception(f"Model file not found at {MODEL_PATH}")
    except Exception as e:
        raise Exception(f"Failed to load model: {e}")


def _injured_players(date, home_team, away_team):
    """Players out for each team: the game's recorded inactive list for a past game, otherwise
    the current injury report (a future game's inactives are not known until the box score)."""
    from datetime import date as _date
    if date < _date.today().isoformat():
        game_id = get_game_id(date, home_team, away_team)
        if game_id is not None:
            return get_game_injuries(game_id, home_team), get_game_injuries(game_id, away_team)
    return get_current_team_injuries(home_team), get_current_team_injuries(away_team)


@lru_cache(maxsize=128)
def get_cached_team_stats(date, home_team, away_team):
    """Cache rolling team stats (last 10/30/90 games before `date`) for prediction."""
    f = get_game_window_features(date, home_team, away_team)
    return {
        'home_rtg': f['Home ORtg'], 'away_rtg': f['Away ORtg'],
        'home_efg': f['Home eFG%'], 'away_efg': f['Away eFG%'],
        'home_tov': f['Home TOV%'], 'away_tov': f['Away TOV%'],
        'home_orb': f['Home ORB%'], 'away_orb': f['Away ORB%'],
    }


def predict_game_outcome(home_team, away_team, model_data, date=None):
    """
    Predict the outcome of a game (optimized with caching).
    
    Args:
        home_team: Home team city name
        away_team: Away team city name  
        model_data: Loaded model data (from load_model)
        date: Game date (YYYY-MM-DD) or None for default
        
    Returns:
        (winner, confidence) tuple
    """
    # Validate teams
    if home_team not in CURRENT_TEAMS:
        raise ValueError(f"Invalid home team: {home_team}. Must be a valid NBA city name.")
    if away_team not in CURRENT_TEAMS:
        raise ValueError(f"Invalid away team: {away_team}. Must be a valid NBA city name.")
    
    # Use provided date or default
    if date is None:
        prediction_date = "2025-04-14"
    else:
        try:
            datetime.strptime(date, "%Y-%m-%d")
            prediction_date = date
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format")
    
    # Extract model
    rf_model = model_data['model']
    
    # Get cached team stats
    stats = get_cached_team_stats(prediction_date, home_team, away_team)
    
    # Back-to-back flags come from the schedule (games played the day before `prediction_date`)
    home_b2b, away_b2b = scrape_back_to_back(prediction_date, home_team, away_team)

    # Build input in the exact column order the model was trained on. Every feature is
    # computed only from games before prediction_date, matching training.
    home_injured, away_injured = _injured_players(prediction_date, home_team, away_team)
    available = {
        "Home ORtg": stats['home_rtg'], "Away ORtg": stats['away_rtg'],
        "Home eFG%": stats['home_efg'], "Away eFG%": stats['away_efg'],
        "Home TOV%": stats['home_tov'], "Away TOV%": stats['away_tov'],
        "Home ORB%": stats['home_orb'], "Away ORB%": stats['away_orb'],
        "Home B2B": home_b2b, "Away B2B": away_b2b,
    }
    if any('Injury' in f for f in model_data['features']):
        available.update({
            "Home Injury Value": get_injury_value(home_injured, home_team, prediction_date),
            "Away Injury Value": get_injury_value(away_injured, away_team, prediction_date),
            "Home Injury Advanced": get_injury_advanced(home_injured, home_team, prediction_date),
            "Away Injury Advanced": get_injury_advanced(away_injured, away_team, prediction_date),
        })
    features = model_data['features']
    unsupported = [f for f in features if f not in available]
    if unsupported:
        raise ValueError(f"Model needs features the backend cannot compute: {unsupported}. "
                         f"Retrain with pipeline/train_model.py.")
    import pandas as pd
    input_data = {f: [available[f]] for f in features}

    # Predict
    prediction_df = pd.DataFrame(input_data)
    prediction = rf_model.predict(prediction_df)
    confidence = rf_model.predict_proba(prediction_df)[0]
    
    # Determine winner
    winner = home_team if prediction[0] == 1 else away_team
    confidence_value = max(confidence)
    
    return winner, confidence_value


def get_model_info(model_data):
    """Get information about the model."""
    return {
        "accuracy": round(model_data.get('accuracy', 0) * 100, 2),
        "features": len(model_data.get('features', [])),
        "model_type": "Random Forest Classifier"
    }


def get_team_comparison_stats(home_team, away_team, date=None):
    """Get detailed comparison stats (optimized with caching)."""
    from datetime import datetime
    
    # Validate teams
    if home_team not in CURRENT_TEAMS:
        raise ValueError(f"Invalid home team: {home_team}")
    if away_team not in CURRENT_TEAMS:
        raise ValueError(f"Invalid away team: {away_team}")
    
    # Use provided date or default
    prediction_date = date if date else "2025-04-14"
    
    try:
        datetime.strptime(prediction_date, "%Y-%m-%d")
    except ValueError:
        raise ValueError("Date must be in YYYY-MM-DD format")
    
    # Get cached stats
    stats = get_cached_team_stats(prediction_date, home_team, away_team)
    
    # Get current injuries (from the DB, refreshed by pipeline/scrape_teams.py)
    home_injuries = get_current_team_injuries(home_team)
    away_injuries = get_current_team_injuries(away_team)

    home_b2b, away_b2b = scrape_back_to_back(prediction_date, home_team, away_team)

    # Determine advantages
    def get_advantage(home_val, away_val, lower_is_better=False):
        if abs(home_val - away_val) < 0.1:
            return "even"
        if lower_is_better:
            return "home" if home_val < away_val else "away"
        return "home" if home_val > away_val else "away"
    
    return {
        "home_team": home_team,
        "away_team": away_team,
        "stats": [
            {
                "metric": "Off Rating",
                "home": f"{stats['home_rtg']:.1f}",
                "away": f"{stats['away_rtg']:.1f}",
                "advantage": get_advantage(stats['home_rtg'], stats['away_rtg'])
            },
            {
                "metric": "eFG%",
                "home": f"{stats['home_efg']:.1f}%",
                "away": f"{stats['away_efg']:.1f}%",
                "advantage": get_advantage(stats['home_efg'], stats['away_efg'])
            },
            {
                "metric": "TOV%",
                "home": f"{stats['home_tov']:.1f}%",
                "away": f"{stats['away_tov']:.1f}%",
                "advantage": get_advantage(stats['home_tov'], stats['away_tov'], lower_is_better=True)
            },
            {
                "metric": "ORB%",
                "home": f"{stats['home_orb']:.1f}%",
                "away": f"{stats['away_orb']:.1f}%",
                "advantage": get_advantage(stats['home_orb'], stats['away_orb'])
            },
            {
                "metric": "Injury Impact",
                "home": "High" if len(home_injuries or []) > 2 else "Medium" if len(home_injuries or []) > 0 else "Low",
                "away": "High" if len(away_injuries or []) > 2 else "Medium" if len(away_injuries or []) > 0 else "Low",
                "advantage": get_advantage(len(away_injuries or []), len(home_injuries or []))
            },
            {
                "metric": "Back-to-Back",
                "home": "Yes" if home_b2b else "No",
                "away": "Yes" if away_b2b else "No",
                "advantage": "even" if home_b2b == away_b2b else ("away" if home_b2b else "home")
            }
        ],
        "breakdown": {
            "home": {
                "off_rtg": stats['home_rtg'],
                "efg_pct": stats['home_efg'],
                "tov_pct": stats['home_tov'],
                "orb_pct": stats['home_orb']
            },
            "away": {
                "off_rtg": stats['away_rtg'],
                "efg_pct": stats['away_efg'],
                "tov_pct": stats['away_tov'],
                "orb_pct": stats['away_orb']
            }
        }
    }