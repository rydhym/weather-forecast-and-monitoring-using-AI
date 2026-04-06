const { logger, responseFormatter } = require('../utils/logger');

const errorHandler = (err, req, res, next) => {
  logger.error(err.message, err);
  const statusCode = res.statusCode === 200 ? 500 : res.statusCode;
  return responseFormatter.error(res, err.message, statusCode);
};

module.exports = errorHandler;
