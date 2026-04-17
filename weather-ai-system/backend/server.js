require('dotenv').config({ path: '../.env' });
const mongoose = require('mongoose');
const app = require('./app');
const { logger } = require('./utils/logger');

const PORT = process.env.PORT || 5000;
const MONGODB_URI = process.env.MONGODB_URI || 'mongodb://localhost:27017/weather-ai-db';

// Start server immediately — don't wait for MongoDB
app.listen(PORT, () => {
  logger.info(`Server running on port ${PORT}`);
});

// Connect to MongoDB in background (non-blocking)
// If it fails, the app still works — alerts just won't persist to DB
mongoose.connect(MONGODB_URI, { tls: true, tlsAllowInvalidCertificates: false })
  .then(() => {
    logger.info('Connected to MongoDB');
  })
  .catch((err) => {
    logger.error('MongoDB connection failed (app still running):', err.message);
    logger.warn('Alert persistence is disabled — alerts will be generated but not saved to DB');
  });
