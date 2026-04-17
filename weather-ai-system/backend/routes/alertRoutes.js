const express = require('express');
const router  = express.Router();
const { getAlerts } = require('../controllers/alertController');

// GET /api/alerts?city=London
// Returns real dynamic alerts generated from live weather + AI prediction
router.get('/', getAlerts);

module.exports = router;
