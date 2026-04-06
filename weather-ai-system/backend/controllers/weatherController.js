const weatherService = require('../services/weatherService');
const { responseFormatter } = require('../utils/logger');

const getWeather = async (req, res, next) => {
  try {
    const city = req.query.city || 'London';
    const weatherData = await weatherService.fetchWeatherData(city);
    return responseFormatter.success(res, weatherData, 'Weather data retrieved successfully');
  } catch (error) {
    next(error);
  }
};

module.exports = {
  getWeather
};
