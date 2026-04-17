/**
 * AI Service — Bridges Express.js backend with Flask AI API
 *
 * FIXES applied:
 *   1. Uses real city coordinates (lat/lon from WeatherAPI) instead of hardcoded London
 *   2. Fetches real 7-day historical weather from Open-Meteo archive API
 *      so lag features in the ML model receive actual data, not random noise
 *
 * Flow:
 *   Express receives request
 *     → fetchRealHistory() calls Open-Meteo for last 7 days
 *     → getRainPrediction() sends real data to Flask
 *     → Flask runs XGBoost model → returns probability
 *     → Express sends to frontend
 *
 * Graceful fallback:
 *   If Flask is down → returns null (app still shows weather, just no AI prediction)
 *   If Open-Meteo is down → falls back to estimates based on current weather
 */

const axios = require('axios');
const { logger } = require('../utils/logger');

// URL of the Flask AI API (default: localhost:5001)
const AI_ENGINE_URL = process.env.AI_ENGINE_URL || 'http://localhost:5001';

// Open-Meteo archive API — free, no API key needed
// Used to get the last 7 days of real weather for a city
const OPEN_METEO_ARCHIVE_URL = 'https://archive-api.open-meteo.com/v1/archive';

/**
 * Fetch real historical weather for a city from Open-Meteo.
 * Returns last 7 days of daily rain, temp, pressure, humidity, cloud cover.
 *
 * @param {number} lat - City latitude
 * @param {number} lon - City longitude
 * @returns {Array} Array of 7 day objects, most recent first
 */
const fetchRealHistory = async (lat, lon) => {
  try {
    // Date range: 8 days ago to 1 day ago (today may be incomplete)
    const now = new Date();
    const end = new Date(now);
    end.setDate(end.getDate() - 1);
    const start = new Date(now);
    start.setDate(start.getDate() - 8);

    const fmt = (d) => d.toISOString().split('T')[0]; // "YYYY-MM-DD"

    const res = await axios.get(OPEN_METEO_ARCHIVE_URL, {
      params: {
        latitude: lat,
        longitude: lon,
        start_date: fmt(start),
        end_date: fmt(end),
        daily: [
          'rain_sum',
          'temperature_2m_mean',
          'pressure_msl_mean',
          'relative_humidity_2m_mean',
          'cloudcover_mean',
        ].join(','),
        timezone: 'auto',
      },
      timeout: 8000,
    });

    const daily = res.data.daily;
    const days = daily.time.map((date, i) => ({
      date,
      rain: daily.rain_sum[i] ?? 0,
      temp_mean: daily.temperature_2m_mean[i] ?? 20,
      pressure: daily.pressure_msl_mean[i] ?? 1013,
      humidity: daily.relative_humidity_2m_mean[i] ?? 60,
      cloud_cover: daily.cloudcover_mean[i] ?? 50,
    }));

    // Return most recent first (index 0 = yesterday, index 6 = 7 days ago)
    return days.reverse();

  } catch (err) {
    logger.warn(`Open-Meteo history fetch failed for (${lat}, ${lon}): ${err.message}. Using fallback estimates.`);
    return null; // caller will handle fallback
  }
};

/**
 * Build fallback history estimates when Open-Meteo is unavailable.
 * Uses current weather values with small random perturbation.
 */
const buildFallbackHistory = (weatherData, days = 7) => {
  return Array.from({ length: days }, (_, i) => ({
    rain: i % 3 === 0 ? 1.5 : 0,           // slight rain pattern
    temp_mean: weatherData.temp + (Math.random() - 0.5) * 4,
    pressure: weatherData.pressure + (Math.random() - 0.5) * 5,
    humidity: weatherData.humidity + (Math.random() - 0.5) * 10,
    cloud_cover: 50,
  }));
};

/**
 * Get rain prediction from the AI engine.
 *
 * @param {Object} weatherData - From weatherService.fetchWeatherData()
 *   Must include: temp, humidity, pressure, windSpeed, latitude, longitude
 * @returns {Object|null} Prediction result or null if AI engine is unavailable
 */
const getRainPrediction = async (weatherData) => {
  try {
    // Use real coordinates from the WeatherAPI response (FIXED — was hardcoded London)
    const lat = weatherData.latitude ?? 51.51;
    const lon = weatherData.longitude ?? -0.13;

    // Build current weather object for Flask
    const current = {
      temp: weatherData.temp,
      humidity: weatherData.humidity,
      pressure: weatherData.pressure,
      wind_speed: weatherData.windSpeed,
      cloud_cover: weatherData.cloudCover ?? 50,
      temp_max: weatherData.temp + 3,
      temp_min: weatherData.temp - 3,
    };

    // Fetch real 7-day history from Open-Meteo (FIXED — was random noise)
    let historyDays = await fetchRealHistory(lat, lon);

    // Fall back to estimates if Open-Meteo is unavailable
    if (!historyDays || historyDays.length < 3) {
      logger.warn('Using fallback history estimates for AI prediction');
      historyDays = buildFallbackHistory(weatherData, 7);
    }

    // history_3d: last 3 days (most recent first)
    const history_3d = historyDays.slice(0, 3);

    // history_7d: full 7 days (most recent first)
    const history_7d = historyDays.slice(0, 7);

    // Build request payload for Flask
    const payload = {
      current,
      history_3d,
      history_7d,
      location: { latitude: lat, longitude: lon }, // FIXED — real coords, not London
    };

    // POST to Flask AI API (5 second timeout)
    const res = await axios.post(`${AI_ENGINE_URL}/predict/rain`, payload, {
      timeout: 5000,
    });

    return res.data.prediction;

  } catch (error) {
    logger.error('AI Engine prediction failed:', error.message);
    return null;
  }
};

/**
 * Get model comparison info from the Flask AI engine.
 * Returns which model won and metrics for all 6 models.
 *
 * @returns {Object|null} Model info or null if unavailable
 */
const getModelInfo = async () => {
  try {
    const res = await axios.get(`${AI_ENGINE_URL}/model/info`, { timeout: 3000 });
    return res.data.model;
  } catch (error) {
    logger.error('AI Engine model info failed:', error.message);
    return null;
  }
};

module.exports = {
  getRainPrediction,
  getModelInfo,
};
