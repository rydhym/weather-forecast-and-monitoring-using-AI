const mongoose = require('mongoose');

const weatherSchema = new mongoose.Schema({
  location: { type: String, required: true },
  temp: { type: Number, required: true },
  humidity: { type: Number, required: true },
  pressure: { type: Number, required: true },
  windSpeed: { type: Number, required: true },
  visibility: { type: Number },
  feelsLike: { type: Number },
  uvIndex: { type: Number },
  condition: { type: String, required: true },
  icon: { type: String },
  forecast: [{
    dt: { type: Number },
    temp: { type: Number },
    condition: { type: String },
    icon: { type: String },
    pop: { type: Number } // Probability of precipitation
  }],
}, { timestamps: true });

module.exports = mongoose.model('WeatherData', weatherSchema);
