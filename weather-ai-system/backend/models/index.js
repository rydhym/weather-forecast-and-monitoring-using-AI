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

const alertSchema = new mongoose.Schema({
  type: { type: String, required: true },
  severity: { type: String, enum: ['advisory', 'watch', 'warning'], required: true },
  title: { type: String, required: true },
  description: { type: String, required: true },
  location: { type: String, required: true },
  expiresAt: { type: Date, required: true },
}, { timestamps: true });

const userSchema = new mongoose.Schema({
  username: { type: String, required: true, unique: true },
  password: { type: String, required: true }, // Should be hashed in production
  savedLocations: [{ type: String }]
}, { timestamps: true });

const WeatherData = mongoose.model('WeatherData', weatherSchema);
const Alert = mongoose.model('Alert', alertSchema);
const User = mongoose.model('User', userSchema);

module.exports = { WeatherData, Alert, User };
