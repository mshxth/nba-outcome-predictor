"""ML model loading and prediction functions for API."""

import pickle
import os
from datetime import datetime

# Import from current directory (backend folder)
from config import TEAM_TO_ABBR
from data import (
    get_input_format, get_avg_rtgs, get_avg_efgs, get_avg_tovs, get_avg_orbs,
    scrape_team_injuries, get_injury_value, get_injury_advanced
)

# Paths - use local files
MODEL_PATH = 'models/trained_model.pkl'


def load_model():
    """Load the trained model from pickle file."""
    try:
        with open(MODEL_PATH, 'rb') as f:
            model_data = pickle.load(f)
        return model_data
    except FileNotFoundError:
        raise Exception(f"Model file not found at {MODEL_PATH}")
    except Exception as e:
        raise Exception(f"Failed to load model: {e}")


def predict_game_outcome(home_team, away_team, model_data, date=None):
    """
    Predict the outcome of a game.
    
    Args:
        home_team: Home team city name
        away_team: Away team city name  
        model_data: Loaded model data (from load_model)
        date: Game date (YYYY-MM-DD) or None for default
        
    Returns:
        (winner, confidence) tuple
    """
    # Validate teams
    if home_team not in TEAM_TO_ABBR:
        raise ValueError(f"Invalid home team: {home_team}. Must be a valid NBA city name.")
    if away_team not in TEAM_TO_ABBR:
        raise ValueError(f"Invalid away team: {away_team}. Must be a valid NBA city name.")
    
    # Use provided date or default
    if date is None:
        prediction_date = "2025-04-14"
    else:
        # Validate date format
        try:
            datetime.strptime(date, "%Y-%m-%d")
            prediction_date = date
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format")
    
    # Extract model and features
    rf_model = model_data['model']
    
    # Get features
    home_rtg, away_rtg = get_input_format(prediction_date, home_team, away_team, get_avg_rtgs)
    home_efg, away_efg = get_input_format(prediction_date, home_team, away_team, get_avg_efgs)
    home_tov, away_tov = get_input_format(prediction_date, home_team, away_team, get_avg_tovs)
    home_orb, away_orb = get_input_format(prediction_date, home_team, away_team, get_avg_orbs)
    
    # Get injuries
    home_injuries = scrape_team_injuries(home_team)
    away_injuries = scrape_team_injuries(away_team)
    
    home_injury_value = get_injury_value(home_injuries, home_team)
    away_injury_value = get_injury_value(away_injuries, away_team)
    
    home_injury_advanced = get_injury_advanced(home_injuries, home_team)
    away_injury_advanced = get_injury_advanced(away_injuries, away_team)
    
    # Build input
    import pandas as pd
    input_data = { 
        "Home ORtg": [home_rtg], 
        "Away ORtg": [away_rtg], 
        "Home eFG%": [home_efg], 
        "Away eFG%": [away_efg], 
        "Home TOV%": [home_tov], 
        "Away TOV%": [away_tov], 
        "Home ORB%": [home_orb], 
        "Away ORB%": [away_orb], 
        "Home Injury Value": [home_injury_value], 
        "Away Injury Value": [away_injury_value],
        "Home Injury Advanced": [home_injury_advanced], 
        "Away Injury Advanced": [away_injury_advanced]
    }
    
    # Predict
    prediction_df = pd.DataFrame(input_data)
    prediction = rf_model.predict(prediction_df)
    confidence = rf_model.predict_proba(prediction_df)[0]
    
    # Determine winner
    winner = home_team if prediction[0] == 1 else away_team
    confidence_value = max(confidence)
    
    return winner, confidence_value


def get_model_info(model_data):
    """
    Get information about the model.
    
    Args:
        model_data: Loaded model data
        
    Returns:
        Dictionary with model information
    """
    return {
        "accuracy": round(model_data.get('accuracy', 0) * 100, 2),
        "features": len(model_data.get('features', [])),
        "model_type": "Random Forest Classifier"
    }


def get_team_comparison_stats(home_team, away_team, date=None):
    """
    Get detailed comparison stats for two teams.
    
    Args:
        home_team: Home team city name
        away_team: Away team city name
        date: Game date (YYYY-MM-DD) or None for default
        
    Returns:
        Dictionary with detailed stats for both teams
    """
    from datetime import datetime
    
    # Validate teams
    if home_team not in TEAM_TO_ABBR:
        raise ValueError(f"Invalid home team: {home_team}")
    if away_team not in TEAM_TO_ABBR:
        raise ValueError(f"Invalid away team: {away_team}")
    
    # Use provided date or default
    prediction_date = date if date else "2025-04-14"
    
    try:
        datetime.strptime(prediction_date, "%Y-%m-%d")
    except ValueError:
        raise ValueError("Date must be in YYYY-MM-DD format")
    
    # Get all the stats used in prediction
    home_rtg, away_rtg = get_input_format(prediction_date, home_team, away_team, get_avg_rtgs)
    home_efg, away_efg = get_input_format(prediction_date, home_team, away_team, get_avg_efgs)
    home_tov, away_tov = get_input_format(prediction_date, home_team, away_team, get_avg_tovs)
    home_orb, away_orb = get_input_format(prediction_date, home_team, away_team, get_avg_orbs)
    
    # Get injuries
    home_injuries = scrape_team_injuries(home_team)
    away_injuries = scrape_team_injuries(away_team)
    
    home_injury_value = get_injury_value(home_injuries, home_team)
    away_injury_value = get_injury_value(away_injuries, away_team)
    
    # Determine advantages
    def get_advantage(home_val, away_val, lower_is_better=False):
        if abs(home_val - away_val) < 0.01:
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
                "home": f"{home_rtg:.1f}",
                "away": f"{away_rtg:.1f}",
                "advantage": get_advantage(home_rtg, away_rtg)
            },
            {
                "metric": "eFG%",
                "home": f"{home_efg:.1f}%",
                "away": f"{away_efg:.1f}%",
                "advantage": get_advantage(home_efg, away_efg)
            },
            {
                "metric": "TOV%",
                "home": f"{home_tov:.1f}%",
                "away": f"{away_tov:.1f}%",
                "advantage": get_advantage(home_tov, away_tov, lower_is_better=True)
            },
            {
                "metric": "ORB%",
                "home": f"{home_orb:.1f}%",
                "away": f"{away_orb:.1f}%",
                "advantage": get_advantage(home_orb, away_orb)
            },
            {
                "metric": "Injury Impact",
                "home": "High" if len(home_injuries or []) > 2 else "Medium" if len(home_injuries or []) > 0 else "Low",
                "away": "High" if len(away_injuries or []) > 2 else "Medium" if len(away_injuries or []) > 0 else "Low",
                "advantage": get_advantage(home_injury_value, away_injury_value)
            },
            {
                "metric": "Back-to-Back",
                "home": "No",  # Would need to implement back-to-back check
                "away": "No",
                "advantage": "even"
            }
        ],
        "breakdown": {
            "home": {
                "off_rtg": home_rtg,
                "efg_pct": home_efg,
                "tov_pct": home_tov,
                "orb_pct": home_orb
            },
            "away": {
                "off_rtg": away_rtg,
                "efg_pct": away_efg,
                "tov_pct": away_tov,
                "orb_pct": away_orb
            }
        }
    }