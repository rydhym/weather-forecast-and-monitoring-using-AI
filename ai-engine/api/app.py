"""
Flask API — Serves ML predictions to the Express.js backend.

What is Flask?
  Flask is a lightweight Python web server (like Express.js but for Python).
  It listens for HTTP requests and returns JSON responses.

Why do we need this?
  - The ML model is in Python (scikit-learn, XGBoost, etc.)
  - Your main backend is in Node.js (Express)
  - Flask bridges them: Express sends weather data → Flask runs the model → returns prediction

Architecture:
  React Frontend (port 3000)
       ↓
  Express Backend (port 5000)  ← your main server
       ↓
  Flask AI API (port 5001)     ← THIS FILE
       ↓
  Trained Model (loaded from .joblib file)

Endpoints:
  GET  /health        → Check if the AI engine is running
  POST /predict/rain  → Send weather data, get rain prediction
  GET  /model/info    → Get model name, metrics, comparison results
"""

import os
import sys

# Add parent directory to path so we can import from inference/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from flask import Flask, request, jsonify
from flask_cors import CORS
from inference.predictor import WeatherPredictor

# Create the Flask app
# Flask(__name__) tells Flask to use this file as the starting point
app = Flask(__name__)

# CORS = Cross-Origin Resource Sharing
# Without this, the Express backend (running on port 5000)
# would be BLOCKED from calling this API (running on port 5001)
# because browsers enforce "same-origin policy"
CORS(app)

# Global variable to hold the loaded model
# We load it once when the first request comes in, then reuse it
# (loading from disk takes ~1 second, but predictions take ~1 millisecond)
predictor = None


def get_predictor():
    """
    Load the model on first use (lazy loading).
    After the first call, the model stays in memory.
    """
    global predictor
    if predictor is None:
        predictor = WeatherPredictor()  # loads model, scaler, metadata from disk
    return predictor


# ============================================================
# ENDPOINT 1: Health Check
# GET /health
#
# Used to verify the AI engine is running.
# Express backend can call this before sending prediction requests.
#
# Response: { "status": "ok", "service": "weather-ai-engine" }
# ============================================================
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "weather-ai-engine"})


# ============================================================
# ENDPOINT 2: Rain Prediction
# POST /predict/rain
#
# This is the main endpoint. Express backend sends current weather
# data + recent history, and this returns the rain prediction.
#
# Expected JSON body:
# {
#   "current": {
#     "temp": 22.5,
#     "humidity": 75,
#     "pressure": 1013,
#     "wind_speed": 15,
#     "cloud_cover": 60,
#     "temp_max": 25,     (optional)
#     "temp_min": 18      (optional)
#   },
#   "history_3d": [
#     {"rain": 2.1, "temp_mean": 20, "pressure": 1010, "humidity": 80},
#     {"rain": 0, "temp_mean": 21, "pressure": 1012, "humidity": 70},
#     {"rain": 0.5, "temp_mean": 19, "pressure": 1008, "humidity": 85}
#   ],
#   "history_7d": [ ... up to 7 days ... ],
#   "location": {"latitude": 51.51, "longitude": -0.13}
# }
#
# Response:
# {
#   "success": true,
#   "prediction": {
#     "will_rain": true,
#     "rain_probability": 0.7823,
#     "confidence": 0.7823,
#     "model_used": "XGBoost"
#   }
# }
# ============================================================
@app.route("/predict/rain", methods=["POST"])
def predict_rain():
    try:
        # Get JSON data from the request body
        data = request.get_json()

        # Validate: request body must exist
        if not data:
            return jsonify({"error": "Request body is required"}), 400

        # Validate: all required fields must be present
        required = ["current", "history_3d", "history_7d", "location"]
        for field in required:
            if field not in data:
                return jsonify({"error": f"Missing field: {field}"}), 400

        # Load model (first time) and make prediction
        pred = get_predictor()
        result = pred.predict_from_current_weather(
            current=data["current"],
            history_3d=data["history_3d"],
            history_7d=data["history_7d"],
            location=data["location"],
        )

        return jsonify({"success": True, "prediction": result})

    except FileNotFoundError as e:
        # Model hasn't been trained yet
        return jsonify({"error": str(e), "hint": "Train the model first"}), 503
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================
# ENDPOINT 3: Model Info
# GET /model/info
#
# Returns information about which model won and how all 6 performed.
# Useful for the Analytics tab on your dashboard.
#
# Response:
# {
#   "success": true,
#   "model": {
#     "model_name": "XGBoost",
#     "metrics": {"accuracy": 0.82, "f1_score": 0.80, ...},
#     "all_models_tested": ["LogisticRegression", "RandomForest", ...],
#     "all_results": { ... each model's metrics ... },
#     "feature_count": 33
#   }
# }
# ============================================================
@app.route("/model/info", methods=["GET"])
def model_info():
    try:
        pred = get_predictor()
        info = pred.get_model_info()
        return jsonify({"success": True, "model": info})
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================
# START THE SERVER
# Runs when you execute: python ai-engine/api/app.py
#
# host="0.0.0.0" means accept connections from any IP (not just localhost)
# port=5001 — Express is on 5000, so this uses 5001 to avoid conflict
# debug=True — auto-restarts when you edit the code (development only)
# ============================================================
if __name__ == "__main__":
    port = int(os.environ.get("AI_ENGINE_PORT", 5001))
    print(f"AI Engine API starting on port {port}")
    app.run(host="0.0.0.0", port=port, debug=True)
