import React, { useEffect, useState, useCallback } from 'react';
import axios from 'axios';
import {
  Search, MapPin, Droplets, Wind, Gauge, Eye, Sun, Thermometer,
  CloudRain, AlertTriangle, TrendingUp, Clock, RefreshCw, CloudSnow,
  Cloud, CloudLightning, CloudDrizzle, CloudFog, SunMedium
} from 'lucide-react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, Legend
} from 'recharts';
import './Dashboard.css';

const API_BASE = 'http://localhost:5000/api';

const getWeatherIcon = (condition, size = 48) => {
  if (!condition) return <SunMedium size={size} />;
  const c = condition.toLowerCase();
  if (c.includes('thunder')) return <CloudLightning size={size} />;
  if (c.includes('drizzle')) return <CloudDrizzle size={size} />;
  if (c.includes('rain')) return <CloudRain size={size} />;
  if (c.includes('snow')) return <CloudSnow size={size} />;
  if (c.includes('cloud')) return <Cloud size={size} />;
  if (c.includes('mist') || c.includes('haze') || c.includes('fog')) return <CloudFog size={size} />;
  return <SunMedium size={size} />;
};

const Dashboard = ({ activeTab, onWeatherUpdate, theme }) => {
  const [weatherData, setWeatherData] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchCity, setSearchCity] = useState('Delhi');
  const [lastUpdated, setLastUpdated] = useState(null);

  const fetchWeather = useCallback(async (city) => {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.get(`${API_BASE}/weather`, { params: { city } });
      const data = res.data.data;
      setWeatherData(data);
      setLastUpdated(new Date());
      if (data.condition) onWeatherUpdate(data.condition, data.temp);
    } catch (err) {
      console.error(err);
      // Fallback to mock data if backend not available
      const conditions = ['Clear', 'Rain', 'Clouds', 'Thunderstorm', 'Snow', 'Mist'];
      const dynamicCondition = conditions[city.length % conditions.length];

      const mock = {
        location: city,
        temp: 20 + (city.length % 15),
        condition: dynamicCondition,
        humidity: 58 + (city.length % 20),
        windSpeed: 12 + (city.length % 10),
        pressure: 1012,
        visibility: 8,
        uvIndex: 7,
        feelsLike: 22 + (city.length % 15),
        icon: '01d',
        forecast: generateMockForecast()
      };
      setWeatherData(mock);
      setLastUpdated(new Date());
      onWeatherUpdate(mock.condition, mock.temp);
      setError('Using simulated offline data — backend not connected');
    }
    setLoading(false);
  }, [onWeatherUpdate]);

  const fetchAlerts = useCallback(async () => {
    try {
      const res = await axios.get(`${API_BASE}/alerts`);
      setAlerts(res.data.data || []);
    } catch {
      setAlerts([
        { id: 1, type: 'Rain', severity: 'warning', title: 'Heavy Rainfall Advisory', description: 'Expected heavy rainfall over the next 4 hours.' },
        { id: 2, type: 'Wind', severity: 'advisory', title: 'Wind Advisory', description: 'Strong winds up to 40 km/h predicted.' }
      ]);
    }
  }, []);

  useEffect(() => {
    fetchWeather(searchCity);
    fetchAlerts();
    // Auto-refresh every 10 minutes (SRS: NFR Performance)
    const interval = setInterval(() => fetchWeather(searchCity), 600000);
    return () => clearInterval(interval);
  }, []);

  const handleSearch = (e) => {
    e.preventDefault();
    if (searchCity.trim()) fetchWeather(searchCity.trim());
  };

  // Prepare forecast chart data
  const hourlyData = weatherData?.forecast?.slice(0, 8).map((f, i) => ({
    time: new Date(f.dt * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    temp: Math.round(f.temp),
    rain: Math.round(f.pop || 0),
  })) || [];

  const dailyData = weatherData?.forecast
    ? aggregateDailyForecast(weatherData.forecast)
    : [];

  const rainfallProbability = weatherData?.forecast?.[0]?.pop ?? 0;

  return (
    <main className="main-content">
      {/* Top Bar */}
      <div className="top-bar">
        <div>
          <h2>
            {activeTab === 'dashboard' && 'Weather Dashboard'}
            {activeTab === 'forecast' && 'Forecast'}
            {activeTab === 'alerts' && 'Weather Alerts'}
            {activeTab === 'analytics' && 'Analytics'}
          </h2>
          {lastUpdated && (
            <span className="last-updated">
              <Clock size={12} /> Updated {lastUpdated.toLocaleTimeString()}
            </span>
          )}
        </div>
        <div className="top-bar-right">
          <span className="theme-label">{theme} theme</span>
          <form className="search-wrapper" onSubmit={handleSearch}>
            <Search size={16} color="var(--text-muted)" />
            <input
              type="text"
              placeholder="Search city..."
              value={searchCity}
              onChange={(e) => setSearchCity(e.target.value)}
            />
            <button type="submit" className="search-btn">Go</button>
          </form>
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {loading ? (
        <div className="loading-state">
          <RefreshCw size={32} className="spin" />
          <p>Fetching weather data...</p>
        </div>
      ) : (
        <>
          {/* ===== DASHBOARD TAB ===== */}
          {activeTab === 'dashboard' && (
            <div className="dashboard-grid">
              {/* Current Weather Card */}
              <div className="card current-weather-card">
                <div className="current-weather-top">
                  <div>
                    <div className="current-temp">{Math.round(weatherData?.temp)}°</div>
                    <div className="current-condition">{weatherData?.condition}</div>
                    <div className="current-location">
                      <MapPin size={14} />
                      {weatherData?.location}
                    </div>
                  </div>
                  <div className="current-weather-icon">
                    {getWeatherIcon(weatherData?.condition, 64)}
                  </div>
                </div>
                <div className="current-feels">
                  Feels like {Math.round(weatherData?.feelsLike)}°C
                </div>
              </div>

              {/* Rainfall Probability Card (SRS REQ-12) */}
              <div className="card rainfall-card">
                <div className="card-header">
                  <Droplets size={18} style={{ color: '#3b82f6' }} />
                  <span>Rainfall Probability</span>
                </div>
                <div className="rainfall-gauge">
                  <svg viewBox="0 0 120 120" className="circular-progress">
                    <circle cx="60" cy="60" r="50" className="progress-bg" />
                    <circle
                      cx="60" cy="60" r="50"
                      className="progress-fill"
                      style={{
                        strokeDasharray: `${rainfallProbability * 3.14} 314`,
                        stroke: '#3b82f6'
                      }}
                    />
                  </svg>
                  <div className="rainfall-value">{Math.round(rainfallProbability)}%</div>
                </div>
                <div className="rainfall-label">
                  {rainfallProbability > 70 ? 'High chance of rain' :
                    rainfallProbability > 40 ? 'Moderate chance' : 'Low chance'}
                </div>
              </div>

              {/* Metric Cards */}
              <div className="card metric-small">
                <Droplets size={20} className="metric-icon" style={{ color: '#3b82f6' }} />
                <div className="metric-info">
                  <span className="metric-label">Humidity</span>
                  <span className="metric-val">{weatherData?.humidity}%</span>
                </div>
              </div>
              <div className="card metric-small">
                <Wind size={20} className="metric-icon" />
                <div className="metric-info">
                  <span className="metric-label">Wind Speed</span>
                  <span className="metric-val">{Math.round(weatherData?.windSpeed)} km/h</span>
                </div>
              </div>
              <div className="card metric-small">
                <Gauge size={20} className="metric-icon" />
                <div className="metric-info">
                  <span className="metric-label">Pressure</span>
                  <span className="metric-val">{weatherData?.pressure} hPa</span>
                </div>
              </div>
              <div className="card metric-small">
                <Eye size={20} className="metric-icon" />
                <div className="metric-info">
                  <span className="metric-label">Visibility</span>
                  <span className="metric-val">{weatherData?.visibility} km</span>
                </div>
              </div>
              <div className="card metric-small">
                <Sun size={20} className="metric-icon" />
                <div className="metric-info">
                  <span className="metric-label">UV Index</span>
                  <span className="metric-val">{weatherData?.uvIndex}</span>
                </div>
              </div>
              <div className="card metric-small">
                <Thermometer size={20} className="metric-icon" />
                <div className="metric-info">
                  <span className="metric-label">Feels Like</span>
                  <span className="metric-val">{Math.round(weatherData?.feelsLike)}°C</span>
                </div>
              </div>

              {/* Hourly Forecast Mini Chart */}
              <div className="card chart-card">
                <div className="card-header">
                  <TrendingUp size={18} />
                  <span>Next 24 Hours</span>
                </div>
                <ResponsiveContainer width="100%" height={200}>
                  <AreaChart data={hourlyData}>
                    <defs>
                      <linearGradient id="tempGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="var(--accent)" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="var(--accent)" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                    <XAxis dataKey="time" tick={{ fontSize: 11, fill: 'var(--text-muted)', fontWeight: 700 }} />
                    <YAxis tick={{ fontSize: 11, fill: 'var(--text-muted)', fontWeight: 700 }} />
                    <Tooltip
                      contentStyle={{
                        background: 'var(--bg-card)',
                        border: '1px solid var(--border)',
                        borderRadius: '8px',
                        fontSize: '12px',
                        fontWeight: 700
                      }}
                    />
                    <Area type="monotone" dataKey="temp" stroke="var(--accent)" fill="url(#tempGrad)" name="Temp °C" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>

              {/* Latest Alerts Preview */}
              <div className="card alerts-preview-card">
                <div className="card-header">
                  <AlertTriangle size={18} />
                  <span>Active Alerts</span>
                </div>
                {alerts.length === 0 ? (
                  <p className="no-alerts">No active weather alerts</p>
                ) : (
                  alerts.slice(0, 2).map(alert => (
                    <div key={alert.id} className={`alert-item severity-${alert.severity}`}>
                      <AlertTriangle size={16} />
                      <div>
                        <strong>{alert.title}</strong>
                        <p>{alert.description}</p>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {/* ===== FORECAST TAB (SRS REQ-6,7,8) ===== */}
          {activeTab === 'forecast' && (
            <div className="forecast-section">
              {/* Hourly */}
              <div className="card">
                <div className="card-header">
                  <Clock size={18} />
                  <span>Hourly Forecast</span>
                </div>
                <div className="hourly-scroll">
                  {weatherData?.forecast?.slice(0, 12).map((f, i) => (
                    <div key={i} className="hourly-item">
                      <span className="hourly-time">
                        {new Date(f.dt * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                      {getWeatherIcon(f.condition, 24)}
                      <span className="hourly-temp">{Math.round(f.temp)}°</span>
                      <span className="hourly-rain"><Droplets size={10} /> {Math.round(f.pop)}%</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Daily */}
              <div className="card">
                <div className="card-header">
                  <TrendingUp size={18} />
                  <span>5-Day Forecast</span>
                </div>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={dailyData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                    <XAxis dataKey="day" tick={{ fontSize: 12, fill: 'var(--text-muted)' }} />
                    <YAxis tick={{ fontSize: 12, fill: 'var(--text-muted)' }} />
                    <Tooltip
                      contentStyle={{
                        background: 'var(--bg-card)',
                        border: '1px solid var(--border)',
                        borderRadius: '8px'
                      }}
                    />
                    <Legend />
                    <Bar dataKey="high" fill="var(--accent)" name="High °C" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="low" fill="var(--text-muted)" name="Low °C" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Rain probability chart */}
              <div className="card">
                <div className="card-header">
                  <CloudRain size={18} />
                  <span>Rainfall Probability Trend</span>
                </div>
                <ResponsiveContainer width="100%" height={250}>
                  <AreaChart data={hourlyData}>
                    <defs>
                      <linearGradient id="rainGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4} />
                        <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                    <XAxis dataKey="time" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
                    <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
                    <Tooltip
                      contentStyle={{
                        background: 'var(--bg-card)',
                        border: '1px solid var(--border)',
                        borderRadius: '8px'
                      }}
                    />
                    <Area type="monotone" dataKey="rain" stroke="#3b82f6" fill="url(#rainGrad)" name="Rain %" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* ===== ALERTS TAB (SRS REQ-16,17,18) ===== */}
          {activeTab === 'alerts' && (
            <div className="alerts-section">
              <div className="card">
                <div className="card-header">
                  <AlertTriangle size={18} />
                  <span>Weather Alerts</span>
                  <span className="alert-count">{alerts.length} active</span>
                </div>
                {alerts.length === 0 ? (
                  <div className="empty-state">
                    <AlertTriangle size={48} />
                    <p>No active weather alerts for {weatherData?.location}</p>
                  </div>
                ) : (
                  <div className="alerts-list">
                    {alerts.map(alert => (
                      <div key={alert.id} className={`alert-card severity-${alert.severity}`}>
                        <div className="alert-card-header">
                          <span className={`severity-badge ${alert.severity}`}>{alert.severity}</span>
                          <span className="alert-type">{alert.type}</span>
                        </div>
                        <h3>{alert.title}</h3>
                        <p>{alert.description}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ===== ANALYTICS TAB (SRS: Weather Analytics Visualization) ===== */}
          {activeTab === 'analytics' && (
            <div className="analytics-section">
              <div className="card">
                <div className="card-header">
                  <TrendingUp size={18} />
                  <span>Temperature Trend</span>
                </div>
                <ResponsiveContainer width="100%" height={300}>
                  <AreaChart data={hourlyData}>
                    <defs>
                      <linearGradient id="tempGrad2" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="var(--accent)" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="var(--accent)" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                    <XAxis dataKey="time" tick={{ fontSize: 12, fill: 'var(--text-muted)' }} />
                    <YAxis tick={{ fontSize: 12, fill: 'var(--text-muted)' }} />
                    <Tooltip
                      contentStyle={{
                        background: 'var(--bg-card)',
                        border: '1px solid var(--border)',
                        borderRadius: '8px'
                      }}
                    />
                    <Area type="monotone" dataKey="temp" stroke="var(--accent)" fill="url(#tempGrad2)" name="Temperature °C" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>

              <div className="analytics-grid">
                <div className="card">
                  <div className="card-header">
                    <Droplets size={18} />
                    <span>Precipitation Forecast</span>
                  </div>
                  <ResponsiveContainer width="100%" height={250}>
                    <BarChart data={hourlyData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                      <XAxis dataKey="time" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
                      <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
                      <Tooltip
                        contentStyle={{
                          background: 'var(--bg-card)',
                          border: '1px solid var(--border)',
                          borderRadius: '8px'
                        }}
                      />
                      <Bar dataKey="rain" fill="#3b82f6" name="Rain %" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>

                <div className="card pattern-card">
                  <div className="card-header">
                    <TrendingUp size={18} />
                    <span>Weather Patterns Detected</span>
                  </div>
                  <div className="patterns-list">
                    {detectPatterns(weatherData).map((pattern, i) => (
                      <div key={i} className={`pattern-item ${pattern.type}`}>
                        <span className="pattern-indicator"></span>
                        <div>
                          <strong>{pattern.title}</strong>
                          <p>{pattern.description}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </main>
  );
};

/* Helper: Generate mock forecast when backend is unavailable */
function generateMockForecast() {
  const now = Math.floor(Date.now() / 1000);
  return Array.from({ length: 40 }, (_, i) => ({
    dt: now + i * 10800,
    temp: 28 + Math.sin(i / 3) * 6,
    condition: i % 5 === 0 ? 'Rain' : 'Clear',
    icon: i % 5 === 0 ? '10d' : '01d',
    pop: Math.max(0, Math.min(100, 30 + Math.sin(i / 2) * 40)),
  }));
}

/* Helper: Aggregate 3-hour forecast blocks into daily highs/lows */
function aggregateDailyForecast(forecast) {
  const days = {};
  forecast.forEach(f => {
    const dayKey = new Date(f.dt * 1000).toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' });
    if (!days[dayKey]) days[dayKey] = { high: -Infinity, low: Infinity };
    days[dayKey].high = Math.max(days[dayKey].high, f.temp);
    days[dayKey].low = Math.min(days[dayKey].low, f.temp);
  });
  return Object.entries(days).slice(0, 5).map(([day, d]) => ({
    day,
    high: Math.round(d.high),
    low: Math.round(d.low),
  }));
}

/* Helper: Detect weather patterns from data (SRS REQ-13,14,15) */
function detectPatterns(data) {
  if (!data) return [];
  const patterns = [];
  if (data.pressure < 1005) {
    patterns.push({ type: 'warning', title: 'Low Pressure System', description: `Pressure at ${data.pressure} hPa — possible storm activity.` });
  }
  if (data.humidity > 80) {
    patterns.push({ type: 'info', title: 'High Humidity', description: `Humidity at ${data.humidity}% — increased chance of precipitation.` });
  }
  if (data.windSpeed > 30) {
    patterns.push({ type: 'warning', title: 'Strong Winds', description: `Wind speed ${Math.round(data.windSpeed)} km/h — exercise caution.` });
  }
  if (data.temp > 40) {
    patterns.push({ type: 'danger', title: 'Extreme Heat', description: `Temperature ${Math.round(data.temp)}°C — heat advisory in effect.` });
  }
  if (patterns.length === 0) {
    patterns.push({ type: 'normal', title: 'Normal Conditions', description: 'No unusual weather patterns detected.' });
  }
  return patterns;
}

export default Dashboard;
