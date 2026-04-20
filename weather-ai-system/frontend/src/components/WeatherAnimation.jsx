import React, { useMemo } from 'react';
import './WeatherAnimation.css';

const WeatherAnimation = ({ theme }) => {
  // Generate random particles (memoized so they don't jump around on re-renders)
  const particles = useMemo(() => {
    const generateParticles = (count, className, baseStyle = {}) => {
      return Array.from({ length: count }).map((_, i) => {
        const left = `${Math.random() * 100}%`;
        const animationDuration = `${Math.random() * 2 + 1}s`;
        const animationDelay = `${Math.random() * 2}s`;
        const opacity = Math.random() * 0.5 + 0.3;

        let style = { left, animationDuration, animationDelay, opacity, ...baseStyle };

        if (className === 'snowflake') {
          style.animationDuration = `${Math.random() * 6 + 6}s`;
          style.animationDelay = `-${Math.random() * 6}s`;
          const size = Math.random() * 8 + 6; // bigger snowflakes
          style.width = `${size}px`;
          style.height = `${size}px`;
          style.opacity = Math.random() * 0.4 + 0.6; // brighter
        }

        if (className === 'moving-cloud') {
          style.animationDuration = `${Math.random() * 60 + 50}s`;
          style.animationDelay = `-${Math.random() * 60}s`;
          style.top = `${Math.random() * 50}%`;
          const width = Math.random() * 250 + 200; // bigger clouds
          style.width = `${width}px`;
          style.height = `${width / 2.5}px`;
          style.opacity = Math.random() * 0.3 + 0.25; // much more visible
        }

        if (className === 'rain-drop') {
          style.animationDelay = `-${Math.random() * 2}s`; // random start
        }

        if (className === 'star') {
          style.top = `${Math.random() * 100}%`;
          style.left = `${Math.random() * 100}%`;
          const size = Math.random() * 3 + 1;
          style.width = `${size}px`;
          style.height = `${size}px`;
          style.animationDuration = `${Math.random() * 3 + 2}s`;
          style.animationDelay = `-${Math.random() * 3}s`;
          style.opacity = Math.random() * 0.7 + 0.3;
        }

        return <div key={i} className={className} style={style} />;
      });
    };

    return {
      rain: generateParticles(45, 'rain-drop'),
      snow: generateParticles(80, 'snowflake'),
      clouds: generateParticles(12, 'moving-cloud'),
      stars: generateParticles(120, 'star'),
      thunderClouds: generateParticles(12, 'moving-cloud', { background: '#020617', opacity: 0.9, filter: 'blur(12px)' })
    };
  }, []);

  if (theme === 'clear') {
    return (
      <div className="weather-animation-container">
        <div className="sun-glow" />
        <div className="sun-rays">
          <div className="sun-ray" style={{ '--i': 1 }} />
          <div className="sun-ray" style={{ '--i': 2 }} />
          <div className="sun-ray" style={{ '--i': 3 }} />
          <div className="sun-ray" style={{ '--i': 4 }} />
          <div className="sun-ray" style={{ '--i': 5 }} />
        </div>
        {/* Subtle cloud drift for a lively sky */}
        <div className="subtle-clouds">
          {particles.clouds.slice(0, 4)}
        </div>
        {/* Light reflections / Bokeh effect */}
        <div className="light-reflections">
          <div className="reflection" style={{ top: '20%', left: '30%', animationDelay: '0s' }} />
          <div className="reflection" style={{ top: '60%', left: '80%', animationDelay: '2s' }} />
          <div className="reflection" style={{ top: '40%', left: '10%', animationDelay: '4s' }} />
        </div>
      </div>
    );
  }

  if (theme === 'clear-night') {
    return (
      <div className="weather-animation-container">
        {particles.stars}
        <div className="moon-glow" />
      </div>
    );
  }

  return (
    <div className="weather-animation-container">
      {theme === 'rain' && particles.rain}

      {theme === 'snow' && particles.snow}

      {theme === 'clouds' && particles.clouds}

      {theme === 'thunderstorm' && (
        <>
          <div className="thunder-flash" />
        </>
      )}

      {theme === 'mist' && (
        <>
          {particles.clouds}
          <div className="mist-layer" />
          <div className="mist-layer-2" />
          <div className="mist-layer-3" />
        </>
      )}
    </div>
  );
};

export default WeatherAnimation;
