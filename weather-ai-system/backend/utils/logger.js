const logger = {
  info: (message) => console.log(`[INFO] ${new Date().toISOString()} - ${message}`),
  error: (message, err) => console.error(`[ERROR] ${new Date().toISOString()} - ${message}`, err),
};

const responseFormatter = {
  success: (res, data, message = 'Success') => {
    return res.status(200).json({ success: true, message, data });
  },
  error: (res, error, statusCode = 500) => {
    return res.status(statusCode).json({ success: false, error: error.message || error });
  }
};

module.exports = { logger, responseFormatter };
