"""
Inference Module (v4) — Loads the best trained model and makes predictions.

v4 changes (for pipeline v5):
  - Loads selected_features.joblib for feature selection
  - Falls back to all features if not found (backward compatible)
  - Uses optimal_threshold from metadata
  - Builds city one-hot encoding features via nearest-city lookup
  - Builds climate_zone and is_southern_hemisphere from lat/lon
  - Extended rain lags (5, 7 day) and cloud cover lags
"""

import os
import joblib
import json
import numpy as np

MODELS_DIR = os.path.join(os.path.dirname(__file__), '..', 'models')


class WeatherPredictor:
    """
    Loads the best saved model and provides prediction methods.
    """

    def __init__(self):
        self.model = None
        self.scaler = None
        self.metadata = None
        self.threshold = 0.5
        self.selected_features = None  # v5 feature selection indices
        self._load()

    def _load(self):
        model_path = os.path.join(MODELS_DIR, "best_rain_predictor.joblib")
        scaler_path = os.path.join(MODELS_DIR, "scaler.joblib")
        metadata_path = os.path.join(MODELS_DIR, "model_metadata.json")
        features_path = os.path.join(MODELS_DIR, "selected_features.joblib")

        if not os.path.exists(model_path):
            raise FileNotFoundError(
                "No trained model found. Run ai-engine/training/train_models.py first."
            )

        self.model = joblib.load(model_path)
        self.scaler = joblib.load(scaler_path)

        with open(metadata_path, "r") as f:
            self.metadata = json.load(f)

        self.threshold = self.metadata.get("optimal_threshold", 0.5)

        # Load feature selection indices (v5+)
        if os.path.exists(features_path):
            self.selected_features = joblib.load(features_path)
            print(f"  Loaded feature selection: {len(self.selected_features)} features")
        else:
            self.selected_features = None
            print("  No feature selection file — using all features")

    def predict_rain(self, features_dict):
        """
        Predict rainfall probability from a complete set of features.
        Uses optimal_threshold from training for the yes/no decision.
        If feature selection was used in training, applies the same selection.
        """
        # Use all_feature_columns (v5) or feature_columns (v4) to build the full vector
        all_cols = self.metadata.get("all_feature_columns", self.metadata["feature_columns"])
        feature_values = []

        for col in all_cols:
            if col not in features_dict:
                raise ValueError(f"Missing feature: {col}")
            feature_values.append(float(features_dict[col]))

        X = np.array([feature_values])
        X_scaled = self.scaler.transform(X)

        # Apply feature selection if available (v5+)
        if self.selected_features is not None:
            X_scaled = X_scaled[:, self.selected_features]

        probability = float(self.model.predict_proba(X_scaled)[0][1])
        will_rain = probability >= self.threshold

        return {
            "will_rain": bool(will_rain),
            "rain_probability": round(probability, 4),
            "confidence": round(max(probability, 1 - probability), 4),
            "model_used": self.metadata["best_model"],
        }

    def predict_from_current_weather(self, current, history_3d, history_7d, location):
        """
        Simplified prediction — builds all ~70 features from current weather
        data + recent history + location.
        """
        # Import helpers from preprocessing
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from utils.preprocessing import get_nearest_city, get_climate_zone, KNOWN_CITIES

        today = current
        h = history_3d

        lat = location["latitude"]
        lon = location["longitude"]

        # ----------------------------------------------------------
        # LAG FEATURES
        # ----------------------------------------------------------
        rain_lags = [h[i].get("rain", 0) for i in range(min(3, len(h)))]
        temp_lags = [h[i].get("temp_mean", today["temp"]) for i in range(min(3, len(h)))]
        pressure_lags = [h[i].get("pressure", today["pressure"]) for i in range(min(3, len(h)))]
        humidity_lags = [h[i].get("humidity", today["humidity"]) for i in range(min(3, len(h)))]

        while len(rain_lags) < 3:
            rain_lags.append(0)
        while len(temp_lags) < 3:
            temp_lags.append(today["temp"])
        while len(pressure_lags) < 3:
            pressure_lags.append(today["pressure"])
        while len(humidity_lags) < 3:
            humidity_lags.append(today["humidity"])

        # Extended rain lags (5 and 7 day)
        rain_lag_5 = history_7d[4].get("rain", 0) if len(history_7d) > 4 else 0
        rain_lag_7 = history_7d[6].get("rain", 0) if len(history_7d) > 6 else 0

        # Cloud cover lags
        cloud_lag_1 = h[0].get("cloud_cover", today.get("cloud_cover", 50)) if len(h) > 0 else today.get("cloud_cover", 50)
        cloud_lag_2 = h[1].get("cloud_cover", today.get("cloud_cover", 50)) if len(h) > 1 else today.get("cloud_cover", 50)

        # ----------------------------------------------------------
        # ROLLING AVERAGES
        # ----------------------------------------------------------
        rain_vals_3d = [d.get("rain", 0) for d in history_3d[:3]]
        rain_vals_7d = [d.get("rain", 0) for d in history_7d[:7]]
        temp_vals_3d = [d.get("temp_mean", today["temp"]) for d in history_3d[:3]]
        temp_vals_7d = [d.get("temp_mean", today["temp"]) for d in history_7d[:7]]
        pressure_vals_3d = [d.get("pressure", today["pressure"]) for d in history_3d[:3]]
        pressure_vals_7d = [d.get("pressure", today["pressure"]) for d in history_7d[:7]]
        humidity_vals_3d = [d.get("humidity", today["humidity"]) for d in history_3d[:3]]
        humidity_vals_7d = [d.get("humidity", today["humidity"]) for d in history_7d[:7]]
        cloud_vals_3d = [d.get("cloud_cover", 50) for d in history_3d[:3]]
        cloud_vals_7d = [d.get("cloud_cover", 50) for d in history_7d[:7]]

        # ----------------------------------------------------------
        # TIME FEATURES
        # ----------------------------------------------------------
        import datetime
        now = datetime.datetime.now()
        month = now.month
        doy = now.timetuple().tm_yday

        # ----------------------------------------------------------
        # DERIVED VALUES
        # ----------------------------------------------------------
        temp_max = today.get("temp_max", today["temp"] + 3)
        temp_min = today.get("temp_min", today["temp"] - 3)
        temp_mean = today["temp"]
        humidity = today["humidity"]
        pressure = today["pressure"]
        wind_speed = today["wind_speed"]
        cloud_cover = today.get("cloud_cover", 50)
        solar_radiation = today.get("solar_radiation", 15.0)
        evapotranspiration = today.get("evapotranspiration", 3.0)
        wind_direction = today.get("wind_direction", 180)

        dew_point = temp_mean - ((100 - humidity) / 5.0)
        dew_point_depression = temp_mean - dew_point

        # Rain today flag
        today_rain = today.get("rain", rain_lags[0] if rain_lags else 0)
        rain_today = 1 if today_rain > 0.1 else 0

        # Rain streak
        rain_streak = 0
        for d in history_3d:
            if d.get("rain", 0) > 0.1:
                rain_streak += 1
            else:
                break

        # ----------------------------------------------------------
        # CITY ONE-HOT ENCODING (nearest-city lookup)
        # ----------------------------------------------------------
        nearest = get_nearest_city(lat, lon)
        city_features = {}
        for city_name in KNOWN_CITIES:
            col = f"city_{city_name.lower().replace(' ', '_').replace('ã', 'a')}"
            city_features[col] = 1 if city_name == nearest else 0

        # ----------------------------------------------------------
        # ASSEMBLE ALL FEATURES
        # ----------------------------------------------------------
        features = {
            # Raw measurements (9)
            "temp_max": temp_max,
            "temp_min": temp_min,
            "temp_mean": temp_mean,
            "humidity_mean": humidity,
            "pressure_mean": pressure,
            "wind_speed_max": wind_speed,
            "cloud_cover": cloud_cover,
            "solar_radiation": solar_radiation,
            "evapotranspiration": evapotranspiration,

            # Derived features (9)
            "temp_range": temp_max - temp_min,
            "rain_today": rain_today,
            "dew_point": dew_point,
            "dew_point_depression": dew_point_depression,
            "wind_dir_sin": float(np.sin(2 * np.pi * wind_direction / 360)),
            "wind_dir_cos": float(np.cos(2 * np.pi * wind_direction / 360)),
            "humidity_pressure_ratio": humidity / (pressure + 1e-6),
            "wind_cloud_interaction": wind_speed * cloud_cover / 100.0,
            "moisture_index": (100 - dew_point_depression) * cloud_cover / 100.0,
            "temp_humidity_interaction": temp_mean * humidity / 100.0,

            # Time encoding (4)
            "month_sin": float(np.sin(2 * np.pi * month / 12)),
            "month_cos": float(np.cos(2 * np.pi * month / 12)),
            "doy_sin": float(np.sin(2 * np.pi * doy / 365)),
            "doy_cos": float(np.cos(2 * np.pi * doy / 365)),

            # Lag features (16)
            "rain_lag_1": rain_lags[0],
            "rain_lag_2": rain_lags[1],
            "rain_lag_3": rain_lags[2],
            "rain_lag_5": rain_lag_5,
            "rain_lag_7": rain_lag_7,
            "temp_mean_lag_1": temp_lags[0],
            "temp_mean_lag_2": temp_lags[1],
            "temp_mean_lag_3": temp_lags[2],
            "pressure_lag_1": pressure_lags[0],
            "pressure_lag_2": pressure_lags[1],
            "pressure_lag_3": pressure_lags[2],
            "humidity_lag_1": humidity_lags[0],
            "humidity_lag_2": humidity_lags[1],
            "humidity_lag_3": humidity_lags[2],
            "cloud_cover_lag_1": cloud_lag_1,
            "cloud_cover_lag_2": cloud_lag_2,

            # Rain streak (1)
            "rain_streak": rain_streak,

            # Rolling averages (10)
            "rain_rolling_3d": np.mean(rain_vals_3d) if rain_vals_3d else 0,
            "rain_rolling_7d": np.mean(rain_vals_7d) if rain_vals_7d else 0,
            "temp_rolling_3d": np.mean(temp_vals_3d) if temp_vals_3d else temp_mean,
            "temp_rolling_7d": np.mean(temp_vals_7d) if temp_vals_7d else temp_mean,
            "pressure_rolling_3d": np.mean(pressure_vals_3d) if pressure_vals_3d else pressure,
            "pressure_rolling_7d": np.mean(pressure_vals_7d) if pressure_vals_7d else pressure,
            "humidity_rolling_3d": np.mean(humidity_vals_3d) if humidity_vals_3d else humidity,
            "humidity_rolling_7d": np.mean(humidity_vals_7d) if humidity_vals_7d else humidity,
            "cloud_rolling_3d": np.mean(cloud_vals_3d) if cloud_vals_3d else cloud_cover,
            "cloud_rolling_7d": np.mean(cloud_vals_7d) if cloud_vals_7d else cloud_cover,

            # Change features (5)
            "pressure_change_1d": pressure - pressure_lags[0] if pressure_lags else 0,
            "pressure_change_3d": pressure - pressure_lags[2] if len(pressure_lags) >= 3 else 0,
            "humidity_change_1d": humidity - humidity_lags[0] if humidity_lags else 0,
            "humidity_change_3d": humidity - humidity_lags[2] if len(humidity_lags) >= 3 else 0,
            "cloud_change_1d": cloud_cover - cloud_lag_1,

            # Location + geography (4)
            "latitude": lat,
            "longitude": lon,
            "climate_zone": get_climate_zone(lat),
            "is_southern_hemisphere": 1 if lat < 0 else 0,

            # City one-hot encoding (12)
            **city_features,
        }

        return self.predict_rain(features)

    def get_model_info(self):
        """
        Return metadata about the current model.
        Used by the /model/info API endpoint.
        
        Returns info like:
            {
                "model_name": "XGBoost",
                "metrics": {"accuracy": 0.82, "f1_score": 0.80, ...},
                "all_models_tested": ["LogisticRegression", "RandomForest", ...],
                "all_results": { ... metrics for each model ... },
                "feature_count": 33
            }
        """
        return {
            "model_name": self.metadata["best_model"],
            "metrics": self.metadata["metrics"],
            "all_models_tested": list(self.metadata["all_results"].keys()),
            "all_results": self.metadata["all_results"],
            "feature_count": len(self.metadata["feature_columns"]),
        }
