"""
Weather Data Collection Script
Fetches historical weather data from Open-Meteo (free, no API key needed)
and saves it as CSV for ML training.
"""

import os
import requests
import pandas as pd
import time
from datetime import datetime, timedelta

# Path where raw CSV files will be saved
RAW_DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'ai-engine', 'datasets', 'raw')

# 15 Indian cities with their coordinates (latitude, longitude)
# Covering all major Indian climate zones for diverse rain patterns:
#   - Tropical coastal: Mumbai, Chennai, Kochi, Goa
#   - Semi-arid: Delhi, Jaipur, Hyderabad
#   - Humid subtropical: Kolkata, Lucknow, Patna, Bhopal
#   - Highland: Bangalore, Pune
#   - Temperate/humid: Chandigarh, Guwahati
CITIES = {
    'Delhi':       (28.61, 77.21),
    'Mumbai':      (19.08, 72.88),
    'Bangalore':   (12.97, 77.59),
    'Chennai':     (13.08, 80.27),
    'Kolkata':     (22.57, 88.36),
    'Hyderabad':   (17.39, 78.49),
    'Pune':        (18.52, 73.86),
    'Jaipur':      (26.91, 75.79),
    'Lucknow':     (26.85, 80.95),
    'Kochi':       (9.93, 76.27),
    'Chandigarh':  (30.73, 76.77),
    'Guwahati':    (26.14, 91.74),
    'Patna':       (25.60, 85.10),
    'Bhopal':      (23.26, 77.41),
    'Goa':         (15.50, 73.83),
}

# Open-Meteo Archive API — free historical weather data
OPEN_METEO_URL = "https://archive-api.open-meteo.com/v1/archive"


def fetch_historical_data(lat, lon, start_date, end_date):
    """
    Fetch historical weather data for one city from Open-Meteo.
    
    Parameters:
        lat, lon: City coordinates
        start_date, end_date: Date range as strings "YYYY-MM-DD"
    
    Returns:
        pandas DataFrame with daily weather data
    """
    # These are the weather parameters we request from the API
    # Each one becomes a column in our dataset
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "daily": ",".join([
            "temperature_2m_max",       # Highest temp of the day (°C)
            "temperature_2m_min",       # Lowest temp of the day (°C)
            "temperature_2m_mean",      # Average temp of the day (°C)
            "precipitation_sum",        # Total precipitation including snow (mm)
            "rain_sum",                 # Just rainfall (mm) — this is our key target
            "windspeed_10m_max",        # Peak wind speed (km/h)
            "winddirection_10m_dominant", # Dominant wind direction (degrees)
            "relative_humidity_2m_mean",# Average humidity (%)
            "pressure_msl_mean",        # Average sea-level pressure (mb)
            "cloudcover_mean",          # Average cloud coverage (%)
            "shortwave_radiation_sum",  # Solar radiation (MJ/m²) — proxy for sunshine
            "et0_fao_evapotranspiration", # Reference evapotranspiration (mm)
        ]),
        "timezone": "auto",
    }

    # Make the HTTP request to Open-Meteo
    resp = requests.get(OPEN_METEO_URL, params=params, timeout=30)
    resp.raise_for_status()  # Raises error if request failed
    data = resp.json()

    # Convert JSON response into a pandas DataFrame (like a spreadsheet)
    daily = data["daily"]
    df = pd.DataFrame({
        "date": daily["time"],
        "temp_max": daily["temperature_2m_max"],
        "temp_min": daily["temperature_2m_min"],
        "temp_mean": daily["temperature_2m_mean"],
        "precipitation": daily["precipitation_sum"],
        "rain": daily["rain_sum"],
        "wind_speed_max": daily["windspeed_10m_max"],
        "wind_direction": daily["winddirection_10m_dominant"],
        "humidity_mean": daily["relative_humidity_2m_mean"],
        "pressure_mean": daily["pressure_msl_mean"],
        "cloud_cover": daily["cloudcover_mean"],
        "solar_radiation": daily["shortwave_radiation_sum"],
        "evapotranspiration": daily["et0_fao_evapotranspiration"],
    })

    return df


def collect_all():
    """Main function — fetches data for all cities and saves as CSV."""

    # Create the output directory if it doesn't exist
    os.makedirs(RAW_DATA_DIR, exist_ok=True)

    # Date range: last 5 years (minus 5 days buffer since recent data may be incomplete)
    end_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=1825)).strftime("%Y-%m-%d")

    all_frames = []  # Will hold DataFrames for all cities

    for city, (lat, lon) in CITIES.items():
        print(f"Fetching data for {city}...")
        try:
            df = fetch_historical_data(lat, lon, start_date, end_date)

            # Add city name and coordinates as columns
            # (so the model knows which city each row belongs to)
            df["city"] = city
            df["latitude"] = lat
            df["longitude"] = lon
            all_frames.append(df)

            # Save individual city file (useful for debugging)
            city_file = os.path.join(RAW_DATA_DIR, f"{city.lower().replace(' ', '_')}_weather.csv")
            df.to_csv(city_file, index=False)
            print(f"  Saved {len(df)} rows to {city_file}")

        except Exception as e:
            print(f"  Error fetching {city}: {e}")

        # Rate limit: wait 2 seconds between cities to avoid 429 errors
        time.sleep(2)

    # Combine all cities into one big CSV — this is what the model trains on
    if all_frames:
        combined = pd.concat(all_frames, ignore_index=True)
        combined_file = os.path.join(RAW_DATA_DIR, "all_cities_weather.csv")
        combined.to_csv(combined_file, index=False)
        print(f"\nCombined dataset: {len(combined)} rows saved to {combined_file}")

    return combined if all_frames else None


if __name__ == "__main__":
    collect_all()
