import React, { useState, useEffect } from 'react';
import Dashboard from './pages/Dashboard';
import { LayoutDashboard, CloudRain, Bell, BarChart3, CloudSun } from 'lucide-react';
import './theme.css';
import './App.css';

const getThemeFromCondition = (condition) => {
  if (!condition) return 'clear';
  const c = condition.toLowerCase();
  if (c.includes('thunder')) return 'thunderstorm';
  if (c.includes('rain') || c.includes('drizzle')) return 'rain';
  if (c.includes('snow')) return 'snow';
  if (c.includes('cloud')) return 'clouds';
  if (c.includes('mist') || c.includes('haze') || c.includes('fog') || c.includes('smoke')) return 'mist';
  return 'clear';
};

function App() {
  const [weatherCondition, setWeatherCondition] = useState('Clear');
  const [activeTab, setActiveTab] = useState('dashboard');
  const theme = getThemeFromCondition(weatherCondition);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  return (
    <div className="app-layout" data-theme={theme}>
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="brand-icon">
            <CloudSun size={20} />
          </div>
          <h1>WeatherAI</h1>
        </div>
        <nav className="sidebar-nav">
          <a
            href="#"
            className={activeTab === 'dashboard' ? 'active' : ''}
            onClick={(e) => { e.preventDefault(); setActiveTab('dashboard'); }}
          >
            <LayoutDashboard size={18} className="nav-icon" />
            Dashboard
          </a>
          <a
            href="#"
            className={activeTab === 'forecast' ? 'active' : ''}
            onClick={(e) => { e.preventDefault(); setActiveTab('forecast'); }}
          >
            <CloudRain size={18} className="nav-icon" />
            Forecast
          </a>
          <a
            href="#"
            className={activeTab === 'alerts' ? 'active' : ''}
            onClick={(e) => { e.preventDefault(); setActiveTab('alerts'); }}
          >
            <Bell size={18} className="nav-icon" />
            Alerts
          </a>
          <a
            href="#"
            className={activeTab === 'analytics' ? 'active' : ''}
            onClick={(e) => { e.preventDefault(); setActiveTab('analytics'); }}
          >
            <BarChart3 size={18} className="nav-icon" />
            Analytics
          </a>
        </nav>
      </aside>

      {/* Main */}
      <Dashboard
        activeTab={activeTab}
        onWeatherUpdate={setWeatherCondition}
        theme={theme}
      />
    </div>
  );
}

export default App;
