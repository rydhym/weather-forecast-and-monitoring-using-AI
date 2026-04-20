const axios = require('axios');
const { WeatherData } = require('../models');
const { logger } = require('../utils/logger');

const API_KEY = process.env.WEATHER_API_KEY;
const BASE_URL = 'https://api.weatherapi.com/v1';

const fetchWeatherData = async (city) => {
  if (!API_KEY) {
    throw new Error('Weather API Key is missing. Please configure WEATHER_API_KEY in .env file.');
  }

  try {
    // WeatherAPI.com — current + forecast in one call (free tier gives 3 days)
    const res = await axios.get(`${BASE_URL}/forecast.json`, {
      params: { key: API_KEY, q: city, days: 5, aqi: 'no', alerts: 'yes' }
    });

    const data = res.data;
    const current = data.current;
    const location = data.location;

    // Build hourly forecast array from all forecast days
    const fcData = [];
    data.forecast.forecastday.forEach(day => {
      day.hour.forEach(hour => {
        fcData.push({
          dt: Math.floor(new Date(hour.time).getTime() / 1000),
          temp: hour.temp_c,
          condition: hour.condition.text,
          icon: hour.condition.icon,
          pop: hour.chance_of_rain
        });
      });
    });

    const weatherDocument = {
      location: location.name,
      // Real coordinates from WeatherAPI — used by Flask AI engine for city-based features
      latitude: location.lat,
      longitude: location.lon,
      temp: current.temp_c,
      humidity: current.humidity,
      pressure: current.pressure_mb,
      windSpeed: current.wind_kph,
      visibility: current.vis_km,
      feelsLike: current.feelslike_c,
      uvIndex: current.uv,
      condition: current.condition.text,
      icon: current.condition.icon,
      forecast: fcData
    };

    // Try to save to MongoDB (non-blocking — don't crash if DB is down)
    try {
      await WeatherData.findOneAndUpdate(
        { location: location.name },
        weatherDocument,
        { new: true, upsert: true }
      );
    } catch (dbErr) {
      logger.warn(`MongoDB save failed (non-fatal): ${dbErr.message}`);
    }

    return weatherDocument;
  } catch (error) {
    logger.error(`Error fetching weather data for ${city}:`, error);
    const msg = error.response?.data?.error?.message || 'Failed to fetch weather data';
    throw new Error(msg);
  }
};

module.exports = {
  fetchWeatherData
};
