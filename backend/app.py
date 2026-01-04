"""Flask backend for NBA game predictor."""

from flask import Flask, request, jsonify
from flask_cors import CORS

# Import from current directory
from ml_model import load_model, predict_game_outcome, get_model_info

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend

# Load model on startup
print("Loading model...")
model_data = load_model()
print("Model loaded successfully!")


@app.route('/')
def root():
    """Root endpoint - API info."""
    return jsonify({
        "message": "NBA Game Predictor API",
        "version": "1.0.0",
        "endpoints": {
            "GET /api/teams": "List all NBA teams",
            "GET /api/predict": "Predict game outcome (params: home, away, date)",
            "GET /api/stats": "Model statistics",
            "GET /health": "Health check"
        }
    })


@app.route('/health')
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "model_loaded": model_data is not None
    })


@app.route('/api/teams')
def get_teams():
    """Get list of all NBA teams."""
    teams = [
        "Atlanta", "Boston", "Brooklyn", "Charlotte", "Chicago",
        "Cleveland", "Dallas", "Denver", "Detroit", "Golden State",
        "Houston", "Indiana", "LA Clippers", "LA Lakers", "Memphis",
        "Miami", "Milwaukee", "Minnesota", "New Orleans", "New York",
        "Oklahoma City", "Orlando", "Philadelphia", "Phoenix", "Portland",
        "Sacramento", "San Antonio", "Toronto", "Utah", "Washington"
    ]
    return jsonify({"teams": teams})


@app.route('/api/predict')
def predict():
    """
    Predict the outcome of an NBA game.
    
    Query Parameters:
    - home: Home team city (required)
    - away: Away team city (required)
    - date: Game date YYYY-MM-DD (optional)
    
    Returns JSON with:
    - winner: Predicted winning team
    - confidence: Model confidence (0-100%)
    - home_team: Home team name
    - away_team: Away team name
    - prediction_date: Date used for prediction
    """
    # Get parameters
    home = request.args.get('home')
    away = request.args.get('away')
    date = request.args.get('date')
    
    # Validate required parameters
    if not home:
        return jsonify({"error": "Missing required parameter: home"}), 400
    if not away:
        return jsonify({"error": "Missing required parameter: away"}), 400
    
    try:
        # Make prediction
        winner, confidence = predict_game_outcome(home, away, model_data, date)
        
        return jsonify({
            "winner": winner,
            "confidence": round(confidence * 100, 1),
            "home_team": home,
            "away_team": away,
            "prediction_date": date or "2025-04-14"
        })
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Prediction failed: {str(e)}"}), 500


@app.route('/api/stats')
def get_stats():
    """
    Get model statistics and information.
    
    Returns JSON with:
    - accuracy: Model accuracy (0-100%)
    - features: Number of features used
    - model_type: Type of ML model
    """
    try:
        info = get_model_info(model_data)
        return jsonify(info)
    except Exception as e:
        return jsonify({"error": f"Failed to get stats: {str(e)}"}), 500


@app.route('/api/team-comparison')
def get_team_comparison():
    """
    Get detailed team comparison stats.
    
    Query Parameters:
    - home: Home team city (required)
    - away: Away team city (required)
    - date: Game date YYYY-MM-DD (optional)
    """
    from ml_model import get_team_comparison_stats
    
    home = request.args.get('home')
    away = request.args.get('away')
    date = request.args.get('date')
    
    if not home or not away:
        return jsonify({"error": "Missing required parameters"}), 400
    
    try:
        stats = get_team_comparison_stats(home, away, date)
        return jsonify(stats)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to get stats: {str(e)}"}), 500

@app.route('/api/refresh-cache', methods=['POST'])
def refresh_cache():
    """Refresh injury cache (call this daily)."""
    from ml_model import clear_injury_cache
    
    try:
        clear_injury_cache()
        return jsonify({"message": "Cache cleared successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors."""
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors."""
    return jsonify({"error": "Internal server error"}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)