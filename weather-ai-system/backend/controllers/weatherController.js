const weatherService = require('../services/weatherService');
const aiService = require('../services/aiService');
const { responseFormatter } = require('../utils/logger');

// Original endpoint — fetch current weather for a city
const getWeather = async (req, res, next) => {
  try {
    const city = req.query.city || 'London';
    const weatherData = await weatherService.fetchWeatherData(city);
    return responseFormatter.success(res, weatherData, 'Weather data retrieved successfully');
  } catch (error) {
    next(error);
  }
};

// NEW: Get AI rain prediction for a city
// Fetches current weather, sends it to Flask AI API, returns prediction
const getPrediction = async (req, res, next) => {
  try {
    const city = req.query.city || 'London';

    // Step 1: Get current weather from WeatherAPI.com
    const weatherData = await weatherService.fetchWeatherData(city);

    // Step 2: Send weather data to Flask AI API for prediction
    const prediction = await aiService.getRainPrediction(weatherData);

    // If Flask server is down, prediction will be null
    if (!prediction) {
      return responseFormatter.error(res, 'AI engine unavailable. Is the Flask server running on port 5001?', 503);
    }

    // Step 3: Combine weather + prediction and send to frontend
    return responseFormatter.success(res, {
      city: weatherData.location,
      current: {
        temp: weatherData.temp,
        humidity: weatherData.humidity,
        pressure: weatherData.pressure,
        windSpeed: weatherData.windSpeed,
        condition: weatherData.condition,
      },
      prediction,
    }, 'Rain prediction retrieved successfully');
  } catch (error) {
    next(error);
  }
};

// NEW: Get AI model comparison info
// Returns which model won, metrics for all 6 models, etc.
const getModelInfo = async (req, res, next) => {
  try {
    const info = await aiService.getModelInfo();
    if (!info) {
      return responseFormatter.error(res, 'AI engine unavailable', 503);
    }
    return responseFormatter.success(res, info, 'Model info retrieved successfully');
  } catch (error) {
    next(error);
  }
};

module.exports = {
  getWeather,
  getPrediction,
  getModelInfo,
};
