const express = require('express');
const router = express.Router();
const weatherController = require('../controllers/weatherController');

// GET /api/weather?city=London — fetch current weather
router.get('/', weatherController.getWeather);

// GET /api/weather/predict?city=London — get AI rain prediction
router.get('/predict', weatherController.getPrediction);

// GET /api/weather/model — get AI model comparison info
router.get('/model', weatherController.getModelInfo);

module.exports = router;
