/**
 * Alert Controller — Generates real dynamic weather alerts
 *
 * Instead of returning hardcoded strings, this controller:
 *   1. Fetches current weather for the given city
 *   2. Calls the Flask AI engine for rain prediction
 *   3. Generates alerts based on actual conditions + AI prediction
 *   4. Saves alerts to MongoDB (Alert collection)
 *   5. Returns them to the frontend
 *
 * SRS Requirements covered:
 *   REQ-16: System shall generate rainfall alerts
 *   REQ-17: System shall generate storm alerts
 *   REQ-18: System shall notify users through dashboard alerts
 */

const weatherService  = require('../services/weatherService');
const aiService       = require('../services/aiService');
const { Alert }       = require('../models');
const { responseFormatter } = require('../utils/logger');

/**
 * Analyse weather data + AI prediction and produce alert objects.
 *
 * @param {Object} weatherData  - Live weather from WeatherAPI
 * @param {Object|null} prediction - AI prediction from Flask (or null if offline)
 * @returns {Array} Array of alert objects
 */
function generateAlerts(weatherData, prediction) {
  const alerts = [];
  let idCounter = 1;

  // ── AI-based rainfall alert (REQ-16) ─────────────────────────────────────
  if (prediction) {
    const prob = prediction.rain_probability ?? 0;

    if (prob >= 0.75) {
      alerts.push({
        id: idCounter++,
        type: 'Rain',
        severity: 'warning',
        title: 'Heavy Rainfall Alert',
        description: `AI model predicts a ${Math.round(prob * 100)}% chance of rain tomorrow. Carry an umbrella and avoid low-lying areas.`,
        source: 'AI Engine',
        confidence: Math.round(prediction.confidence * 100),
        location: weatherData.location,
        expiresAt: new Date(Date.now() + 24 * 3600 * 1000), // 24 hrs
      });
    } else if (prob >= 0.50) {
      alerts.push({
        id: idCounter++,
        type: 'Rain',
        severity: 'advisory',
        title: 'Rain Advisory',
        description: `AI model predicts a ${Math.round(prob * 100)}% chance of rain tomorrow. Light rain is possible.`,
        source: 'AI Engine',
        confidence: Math.round(prediction.confidence * 100),
        location: weatherData.location,
        expiresAt: new Date(Date.now() + 24 * 3600 * 1000),
      });
    }
  }

  // ── Low pressure system → storm risk (REQ-17) ────────────────────────────
  if (weatherData.pressure < 1000) {
    alerts.push({
      id: idCounter++,
      type: 'Storm',
      severity: 'warning',
      title: 'Low Pressure System Detected',
      description: `Atmospheric pressure at ${weatherData.pressure} hPa — significantly below normal (1013 hPa). Storm activity is likely.`,
      source: 'Pattern Detection',
      location: weatherData.location,
      expiresAt: new Date(Date.now() + 12 * 3600 * 1000),
    });
  } else if (weatherData.pressure < 1005) {
    alerts.push({
      id: idCounter++,
      type: 'Storm',
      severity: 'advisory',
      title: 'Pressure Drop Advisory',
      description: `Pressure at ${weatherData.pressure} hPa — below normal. Monitor for developing weather systems.`,
      source: 'Pattern Detection',
      location: weatherData.location,
      expiresAt: new Date(Date.now() + 12 * 3600 * 1000),
    });
  }

  // ── High winds (REQ-17) ──────────────────────────────────────────────────
  if (weatherData.windSpeed > 50) {
    alerts.push({
      id: idCounter++,
      type: 'Wind',
      severity: 'warning',
      title: 'High Wind Warning',
      description: `Wind speed is ${Math.round(weatherData.windSpeed)} km/h. Secure outdoor objects and avoid travel in exposed areas.`,
      source: 'Live Weather',
      location: weatherData.location,
      expiresAt: new Date(Date.now() + 6 * 3600 * 1000),
    });
  } else if (weatherData.windSpeed > 30) {
    alerts.push({
      id: idCounter++,
      type: 'Wind',
      severity: 'advisory',
      title: 'Wind Advisory',
      description: `Wind gusts up to ${Math.round(weatherData.windSpeed)} km/h detected. Use caution while driving or cycling.`,
      source: 'Live Weather',
      location: weatherData.location,
      expiresAt: new Date(Date.now() + 6 * 3600 * 1000),
    });
  }

  // ── Extreme heat ─────────────────────────────────────────────────────────
  if (weatherData.temp > 42) {
    alerts.push({
      id: idCounter++,
      type: 'Heat',
      severity: 'warning',
      title: 'Extreme Heat Warning',
      description: `Temperature is ${Math.round(weatherData.temp)}°C. Avoid prolonged outdoor exposure. Stay hydrated.`,
      source: 'Live Weather',
      location: weatherData.location,
      expiresAt: new Date(Date.now() + 8 * 3600 * 1000),
    });
  } else if (weatherData.temp > 38) {
    alerts.push({
      id: idCounter++,
      type: 'Heat',
      severity: 'advisory',
      title: 'Heat Advisory',
      description: `Temperature at ${Math.round(weatherData.temp)}°C. Limit strenuous outdoor activities during peak hours.`,
      source: 'Live Weather',
      location: weatherData.location,
      expiresAt: new Date(Date.now() + 8 * 3600 * 1000),
    });
  }

  // ── High humidity with warmth → discomfort ───────────────────────────────
  if (weatherData.humidity > 85 && weatherData.temp > 28) {
    alerts.push({
      id: idCounter++,
      type: 'Humidity',
      severity: 'info',
      title: 'High Humidity Notice',
      description: `Humidity at ${weatherData.humidity}% with ${Math.round(weatherData.temp)}°C temperature. Heat index feels significantly higher. Stay cool.`,
      source: 'Pattern Detection',
      location: weatherData.location,
      expiresAt: new Date(Date.now() + 4 * 3600 * 1000),
    });
  }

  return alerts;
}

/**
 * GET /api/alerts?city=London
 * Generates and returns real dynamic alerts for the given city.
 */
const getAlerts = async (req, res, next) => {
  try {
    const city = req.query.city || 'London';

    // Step 1: Get live weather
    const weatherData = await weatherService.fetchWeatherData(city);

    // Step 2: Get AI prediction (null if Flask offline — non-blocking)
    const prediction = await aiService.getRainPrediction(weatherData);

    // Step 3: Generate alerts from real data
    const alerts = generateAlerts(weatherData, prediction);

    // Step 4: Upsert alerts into MongoDB (clears old ones for this location)
    //   Using deleteMany + insertMany keeps the collection clean
    if (alerts.length > 0) {
      await Alert.deleteMany({ location: weatherData.location });
      const alertDocs = alerts.map(a => ({ ...a, city }));
      await Alert.insertMany(alertDocs).catch(err => {
        // Non-fatal — log but don't crash if DB write fails
        console.warn('Alert DB write failed (non-fatal):', err.message);
      });
    }

    return responseFormatter.success(res, alerts, `${alerts.length} alert(s) generated for ${city}`);

  } catch (error) {
    // If weather fetch fails, fall back to empty alert list
    console.error('Alert generation error:', error.message);
    return responseFormatter.success(res, [], 'No alerts available');
  }
};

module.exports = { getAlerts };
