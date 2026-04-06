const express = require('express');
const router = express.Router();
const { responseFormatter } = require('../utils/logger');
const { Alert } = require('../models');

// GET /api/alerts
router.get('/', async (req, res, next) => {
  try {
    // Mocking alerts for the prototype UI
    const alerts = [
      { id: 1, type: 'Rain', severity: 'warning', title: 'Heavy Rainfall Advisory', description: 'Expected heavy rainfall over the next 4 hours.', location: 'Current Location', expiresAt: new Date(Date.now() + 14400000) },
      { id: 2, type: 'Wind', severity: 'advisory', title: 'Wind Advisory', description: 'Strong winds up to 40 km/h predicted.', location: 'Current Location', expiresAt: new Date(Date.now() + 21600000) }
    ];
    return responseFormatter.success(res, alerts, 'Alerts retrieved successfully');
  } catch (error) {
    next(error);
  }
});

module.exports = router;
