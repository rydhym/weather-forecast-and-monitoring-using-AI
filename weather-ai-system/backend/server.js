require('dotenv').config({ path: '../.env' });
const mongoose = require('mongoose');
const app = require('./app');
const { logger } = require('./utils/logger');

const PORT = process.env.PORT || 5000;
const MONGODB_URI = process.env.MONGODB_URI || 'mongodb://localhost:27017/weather-ai-db';

// Connect to MongoDB
mongoose.connect(MONGODB_URI)
  .then(() => {
    logger.info('Connected to MongoDB');
    // Start Server
    app.listen(PORT, () => {
      logger.info(`Server running on port ${PORT}`);
    });
  })
  .catch((err) => {
    logger.error('Failed to connect to MongoDB', err);
    process.exit(1);
  });
