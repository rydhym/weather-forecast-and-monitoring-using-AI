const express = require('express');
const router = express.Router();
const weatherController = require('../controllers/weatherController');

// GET /api/weather?city=London
router.get('/', weatherController.getWeather);

module.exports = router;
