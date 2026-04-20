"""
Data Preprocessing & Feature Engineering (v3 — accuracy-optimized)
Transforms raw weather CSV data into ML-ready features.

v3 improvements over v2:
  - City one-hot encoding (different cities have very different rain patterns)
  - Climate zone feature (tropical / subtropical / temperate / cold)
  - Extended rain lags (5 and 7 day) for longer temporal memory
  - Cloud cover lag features (clouds today → rain tomorrow)
  - Rain today binary flag (strong signal)
  - Total: ~70 features
"""

import os
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

# Paths to data directories
RAW_DIR = os.path.join(os.path.dirname(__file__), '..', 'datasets', 'raw')
PROCESSED_DIR = os.path.join(os.path.dirname(__file__), '..', 'datasets', 'processed')

# Fixed list of known Indian cities — used for one-hot encoding
# During inference, nearest-city lookup maps any lat/lon to one of these
KNOWN_CITIES = [
    "Bangalore", "Bhopal", "Chandigarh", "Chennai", "Delhi",
    "Goa", "Guwahati", "Hyderabad", "Jaipur", "Kochi",
    "Kolkata", "Lucknow", "Mumbai", "Patna", "Pune",
]

# City coordinates for nearest-city lookup during inference
CITY_COORDS = {
    "Bangalore":  (12.97, 77.59),
    "Bhopal":     (23.26, 77.41),
    "Chandigarh": (30.73, 76.77),
    "Chennai":    (13.08, 80.27),
    "Delhi":      (28.61, 77.21),
    "Goa":        (15.50, 73.83),
    "Guwahati":   (26.14, 91.74),
    "Hyderabad":  (17.39, 78.49),
    "Jaipur":     (26.91, 75.79),
    "Kochi":      (9.93, 76.27),
    "Kolkata":    (22.57, 88.36),
    "Lucknow":    (26.85, 80.95),
    "Mumbai":     (19.08, 72.88),
    "Patna":      (25.60, 85.10),
    "Pune":       (18.52, 73.86),
}


def get_nearest_city(lat, lon):
    """Find the nearest known city to a given lat/lon."""
    min_dist = float("inf")
    nearest = KNOWN_CITIES[0]
    for city, (clat, clon) in CITY_COORDS.items():
        dist = (lat - clat) ** 2 + (lon - clon) ** 2
        if dist < min_dist:
            min_dist = dist
            nearest = city
    return nearest


def get_climate_zone(lat):
    """Classify latitude into a climate zone (0-3)."""
    abs_lat = abs(lat)
    if abs_lat < 23.5:
        return 0  # Tropical
    elif abs_lat < 35:
        return 1  # Subtropical
    elif abs_lat < 55:
        return 2  # Temperate
    else:
        return 3  # Cold


def load_raw_data(filename="all_cities_weather.csv"):
    """
    Load the raw CSV file created by collect_weather_data.py.
    Parses the 'date' column as actual dates (not just strings).
    """
    filepath = os.path.join(RAW_DIR, filename)
    if not os.path.exists(filepath):
        raise FileNotFoundError(
            f"{filepath} not found. Run data-pipeline/collect_weather_data.py first."
        )
    return pd.read_csv(filepath, parse_dates=["date"])


def engineer_features(df):
    """
    Create ML features from raw weather data (v3).
    
    Raw data has ~13 columns per row.
    After this function: ~70 features + 2 target variables.
    """
    df = df.copy()

    # =========================================================
    # A. CITY ONE-HOT ENCODING
    #    Different cities have vastly different rain patterns:
    #    Dubai ~2% rain days, Singapore ~70%, London ~40%
    #    One-hot encoding lets the model learn city-specific patterns
    # =========================================================
    for city_name in KNOWN_CITIES:
        col = f"city_{city_name.lower().replace(' ', '_').replace('ã', 'a')}"
        df[col] = (df["city"] == city_name).astype(int)

    # =========================================================
    # B. CLIMATE ZONE & HEMISPHERE
    #    Groups cities by climate type (tropical, subtropical, etc.)
    # =========================================================
    df["climate_zone"] = df["latitude"].apply(get_climate_zone)
    df["is_southern_hemisphere"] = (df["latitude"] < 0).astype(int)

    # =========================================================
    # C. TIME-BASED FEATURES
    # =========================================================
    df["day_of_year"] = df["date"].dt.dayofyear
    df["month"] = df["date"].dt.month
    df["day_of_week"] = df["date"].dt.dayofweek

    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)
    df["doy_sin"] = np.sin(2 * np.pi * df["day_of_year"] / 365)
    df["doy_cos"] = np.cos(2 * np.pi * df["day_of_year"] / 365)

    # =========================================================
    # D. DERIVED FEATURES
    # =========================================================
    df["temp_range"] = df["temp_max"] - df["temp_min"]
    df["rain_today"] = (df["rain"] > 0.1).astype(int)

    # Dew point approximation (Magnus formula simplified)
    df["dew_point"] = df["temp_mean"] - ((100 - df["humidity_mean"]) / 5.0)
    df["dew_point_depression"] = df["temp_mean"] - df["dew_point"]

    # Wind direction as cyclical features
    df["wind_direction"] = df["wind_direction"].fillna(0)
    df["wind_dir_sin"] = np.sin(2 * np.pi * df["wind_direction"] / 360)
    df["wind_dir_cos"] = np.cos(2 * np.pi * df["wind_direction"] / 360)

    # Fill solar_radiation and evapotranspiration if missing
    df["solar_radiation"] = df["solar_radiation"].fillna(df["solar_radiation"].median())
    df["evapotranspiration"] = df["evapotranspiration"].fillna(df["evapotranspiration"].median())

    # =========================================================
    # E. INTERACTION FEATURES
    # =========================================================
    df["humidity_pressure_ratio"] = df["humidity_mean"] / (df["pressure_mean"] + 1e-6)
    df["wind_cloud_interaction"] = df["wind_speed_max"] * df["cloud_cover"] / 100.0
    df["moisture_index"] = (100 - df["dew_point_depression"]) * df["cloud_cover"] / 100.0
    df["temp_humidity_interaction"] = df["temp_mean"] * df["humidity_mean"] / 100.0

    # =========================================================
    # F. LAG FEATURES — extended to 7 days for rain
    # =========================================================
    df = df.sort_values(["city", "date"])

    for lag in [1, 2, 3]:
        df[f"rain_lag_{lag}"] = df.groupby("city")["rain"].shift(lag)
        df[f"temp_mean_lag_{lag}"] = df.groupby("city")["temp_mean"].shift(lag)
        df[f"pressure_lag_{lag}"] = df.groupby("city")["pressure_mean"].shift(lag)
        df[f"humidity_lag_{lag}"] = df.groupby("city")["humidity_mean"].shift(lag)

    # Extended rain lags (5 and 7 days) — captures weekly rain patterns
    for lag in [5, 7]:
        df[f"rain_lag_{lag}"] = df.groupby("city")["rain"].shift(lag)

    # Cloud cover lags — clouds today/yesterday strongly predict rain tomorrow
    df["cloud_cover_lag_1"] = df.groupby("city")["cloud_cover"].shift(1)
    df["cloud_cover_lag_2"] = df.groupby("city")["cloud_cover"].shift(2)

    # Consecutive rain days (rain streak)
    df["is_rainy"] = (df["rain"] > 0.1).astype(int)
    rain_streak = []
    for _, group in df.groupby("city"):
        streak = []
        count = 0
        for val in group["is_rainy"]:
            if val == 1:
                count += 1
            else:
                count = 0
            streak.append(count)
        rain_streak.extend(streak)
    df["rain_streak"] = rain_streak

    # =========================================================
    # G. ROLLING AVERAGES
    # =========================================================
    for window in [3, 7]:
        df[f"rain_rolling_{window}d"] = (
            df.groupby("city")["rain"]
            .transform(lambda x: x.rolling(window, min_periods=1).mean())
        )
        df[f"temp_rolling_{window}d"] = (
            df.groupby("city")["temp_mean"]
            .transform(lambda x: x.rolling(window, min_periods=1).mean())
        )
        df[f"pressure_rolling_{window}d"] = (
            df.groupby("city")["pressure_mean"]
            .transform(lambda x: x.rolling(window, min_periods=1).mean())
        )
        df[f"humidity_rolling_{window}d"] = (
            df.groupby("city")["humidity_mean"]
            .transform(lambda x: x.rolling(window, min_periods=1).mean())
        )
        df[f"cloud_rolling_{window}d"] = (
            df.groupby("city")["cloud_cover"]
            .transform(lambda x: x.rolling(window, min_periods=1).mean())
        )

    # =========================================================
    # H. CHANGE FEATURES
    # =========================================================
    df["pressure_change_1d"] = df.groupby("city")["pressure_mean"].diff(1)
    df["pressure_change_3d"] = df.groupby("city")["pressure_mean"].diff(3)
    df["humidity_change_1d"] = df.groupby("city")["humidity_mean"].diff(1)
    df["humidity_change_3d"] = df.groupby("city")["humidity_mean"].diff(3)
    df["cloud_change_1d"] = df.groupby("city")["cloud_cover"].diff(1)

    # =========================================================
    # I. TARGET VARIABLES
    # =========================================================
    df["rain_tomorrow"] = (
        df.groupby("city")["rain"].shift(-1).fillna(0) > 0.1
    ).astype(int)

    df["rain_amount_tomorrow"] = df.groupby("city")["rain"].shift(-1).fillna(0)

    # =========================================================
    # J. CLEANUP
    # =========================================================
    df = df.dropna()

    return df


# =========================================================
# CITY ONE-HOT COLUMN NAMES (must match what engineer_features creates)
# =========================================================
CITY_COLUMNS = [
    f"city_{c.lower().replace(' ', '_').replace('ã', 'a')}"
    for c in KNOWN_CITIES
]

# =========================================================
# THE FEATURES — this exact list is what the model expects (~70 features)
# =========================================================
FEATURE_COLUMNS = [
    # Raw weather measurements (9)
    "temp_max", "temp_min", "temp_mean", "humidity_mean", "pressure_mean",
    "wind_speed_max", "cloud_cover", "solar_radiation", "evapotranspiration",

    # Derived features (9)
    "temp_range", "rain_today", "dew_point", "dew_point_depression",
    "wind_dir_sin", "wind_dir_cos",
    "humidity_pressure_ratio", "wind_cloud_interaction", "moisture_index",
    "temp_humidity_interaction",

    # Time encoding (4)
    "month_sin", "month_cos", "doy_sin", "doy_cos",

    # Lag features — 3 days × 4 variables + extended rain lags + cloud lags (18)
    "rain_lag_1", "rain_lag_2", "rain_lag_3", "rain_lag_5", "rain_lag_7",
    "temp_mean_lag_1", "temp_mean_lag_2", "temp_mean_lag_3",
    "pressure_lag_1", "pressure_lag_2", "pressure_lag_3",
    "humidity_lag_1", "humidity_lag_2", "humidity_lag_3",
    "cloud_cover_lag_1", "cloud_cover_lag_2",

    # Rain streak (1)
    "rain_streak",

    # Rolling averages — 2 windows × 5 variables (10)
    "rain_rolling_3d", "rain_rolling_7d",
    "temp_rolling_3d", "temp_rolling_7d",
    "pressure_rolling_3d", "pressure_rolling_7d",
    "humidity_rolling_3d", "humidity_rolling_7d",
    "cloud_rolling_3d", "cloud_rolling_7d",

    # Change features (5)
    "pressure_change_1d", "pressure_change_3d",
    "humidity_change_1d", "humidity_change_3d",
    "cloud_change_1d",

    # Location + geography (4)
    "latitude", "longitude",
    "climate_zone", "is_southern_hemisphere",

    # City one-hot encoding (12)
    *CITY_COLUMNS,
]


def prepare_datasets(df, target="rain_tomorrow", test_size=0.2):
    """
    Split data into train/test sets and scale features.
    """
    X = df[FEATURE_COLUMNS].values
    y = df[target].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42, shuffle=True, stratify=y
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    return X_train_scaled, X_test_scaled, y_train, y_test, scaler


def preprocess_and_save():
    """Run the full preprocessing pipeline and save the result."""
    os.makedirs(PROCESSED_DIR, exist_ok=True)

    df = load_raw_data()
    df = engineer_features(df)

    output_path = os.path.join(PROCESSED_DIR, "features_dataset.csv")
    df.to_csv(output_path, index=False)
    print(f"Processed dataset saved: {len(df)} rows -> {output_path}")
    return df


if __name__ == "__main__":
    preprocess_and_save()
