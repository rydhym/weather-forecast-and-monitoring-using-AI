const express = require('express');
const cors = require('cors');
const weatherRoutes = require('./routes/weatherRoutes');
const alertRoutes = require('./routes/alertRoutes');
const errorHandler = require('./middleware/errorHandler');

const app = express();

// Middleware
app.use(cors());
app.use(express.json());

// Routes
app.use('/api/weather', weatherRoutes);
app.use('/api/alerts', alertRoutes);

// Error Handling Middleware
app.use(errorHandler);

module.exports = app;
