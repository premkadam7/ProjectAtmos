'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState, useEffect } from 'react';

export default function Sidebar() {
  const pathname = usePathname() || '/';

  // State to handle the hover expand/collapse
  const [isExpanded, setIsExpanded] = useState(false);

  // Live weather state
  const [weather, setWeather] = useState({
    temp: '--°C',
    condition: 'Loading...',
    humidity: '--%',
    wind: '-- km/h',
    lastUpdated: 'Fetching...',
    icon: '⛅'
  });
  const [isRefreshing, setIsRefreshing] = useState(false);

  const fetchWeather = async () => {
    setIsRefreshing(true);
    try {
      const res = await fetch('https://api.open-meteo.com/v1/forecast?latitude=28.6139&longitude=77.2090&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code&timezone=auto');
      const data = await res.json();
      const current = data.current;
      
      let condition = 'Clear';
      let icon = '☀️';
      if (current.weather_code >= 1 && current.weather_code <= 3) { condition = 'Partly Cloudy'; icon = '⛅'; }
      if (current.weather_code >= 45 && current.weather_code <= 48) { condition = 'Haze / Fog'; icon = '🌫️'; }
      if (current.weather_code >= 51 && current.weather_code <= 67) { condition = 'Rain'; icon = '🌧️'; }
      if (current.weather_code >= 95) { condition = 'Thunderstorm'; icon = '⛈️'; }

      const date = new Date(current.time);
      const formattedDate = date.toLocaleString('en-IN', {
        day: '2-digit', month: 'short', year: 'numeric',
        hour: '2-digit', minute: '2-digit', hour12: true
      });

      setWeather({
        temp: `${Math.round(current.temperature_2m)}°C`,
        condition: condition,
        humidity: `${current.relative_humidity_2m}%`,
        wind: `${Math.round(current.wind_speed_10m)} km/h`,
        lastUpdated: formattedDate,
        icon: icon
      });
    } catch (error) {
      console.error("Failed to fetch weather", error);
      setWeather(prev => ({ ...prev, condition: 'Failed to load' }));
    }
    setTimeout(() => setIsRefreshing(false), 500); 
  };

  useEffect(() => {
    fetchWeather();
    const interval = setInterval(fetchWeather, 30 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  const navItems = [
    { 
      name: 'Dashboard', path: '/', 
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="3" width="7" height="9" rx="1"></rect><rect x="14" y="3" width="7" height="5" rx="1"></rect><rect x="14" y="12" width="7" height="9" rx="1"></rect><rect x="3" y="16" width="7" height="5" rx="1"></rect>
        </svg>
      )
    },
    { 
      name: 'Forecast Map', path: '/forecast', 
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21"></polygon><line x1="9" y1="3" x2="9" y2="18"></line><line x1="15" y1="6" x2="15" y2="21"></line>
        </svg>
      )
    },
    { 
      name: 'Blame Score', path: '/blame', 
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21.21 15.89A10 10 0 1 1 8 2.83"></path><path d="M22 12A10 10 0 0 0 12 2v10z"></path>
        </svg>
      )
    },
    { 
      name: 'Enforcement', path: '/enforce', 
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
        </svg>
      )
    },
  ];

  return (
    <aside 
      className={`sidebar-glass ${isExpanded ? 'sidebar-expanded' : ''}`}
      onMouseEnter={() => setIsExpanded(true)}
      onMouseLeave={() => setIsExpanded(false)}
      style={{ zIndex: 100 }}
    >
      {/* 1. Logo Section */}
      <div className="sidebar-logo" style={{ minWidth: '240px' }}>
        <div className="logo-icon">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--accent-primary)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M9.59 4.59A2 2 0 1 1 11 8H2m10.59 11.41A2 2 0 1 0 14 16H2m15.73-8.27A2.5 2.5 0 1 1 19.5 12H2"/>
          </svg>
        </div>
        <div className="logo-text" style={{ display: 'flex', flexDirection: 'column' }}>
          <span className="brand" style={{ fontFamily: 'var(--font-display)', fontSize: '26px', fontWeight: 700, letterSpacing: '0.02em', color: 'var(--text-primary)', lineHeight: 1 }}>ATMOS</span>
          <span className="tagline" style={{ fontSize: '11px', color: 'var(--text-dim)', letterSpacing: '0.04em', marginTop: '4px' }}>Air Quality Intelligence</span>
        </div>
      </div>

      {/* 2. Navigation */}
      <nav className="sidebar-nav" style={{ minWidth: '240px' }}>
        {navItems.map((item) => {
          const isActive = pathname === item.path;
          return (
            <Link href={item.path} key={item.name} className={`nav-link ${isActive ? 'active' : ''}`}>
              <div className="nav-icon">{item.icon}</div>
              <span className="nav-label">{item.name}</span>
            </Link>
          );
        })}
      </nav>

      {/* 3. Live Weather Footer */}
      <div className="sidebar-footer" style={{ padding: '20px 16px', display: 'flex', flexDirection: 'column', gap: '20px', borderTop: '1px solid var(--border)', minWidth: '248px', opacity: isExpanded ? 1 : 0, transition: 'opacity 0.2s', pointerEvents: isExpanded ? 'auto' : 'none' }}>
        
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 14px', background: 'var(--bg-tertiary)', borderRadius: '12px', border: '1px solid var(--border)', cursor: 'pointer' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{ fontSize: '18px' }}>🏙️</span>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)', lineHeight: 1.2 }}>Delhi</span>
              <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Change City</span>
            </div>
          </div>
          <span style={{ color: 'var(--text-dim)' }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="6 9 12 15 18 9"></polyline>
            </svg>
          </span>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0 4px' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '24px' }}>{weather.icon}</span>
              <span style={{ fontSize: '20px', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>{weather.temp}</span>
            </div>
            <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>{weather.condition}</span>
          </div>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '11px', color: 'var(--text-secondary)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: '16px' }}>
              <span>Humidity</span>
              <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{weather.humidity}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: '16px' }}>
              <span>Wind</span>
              <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{weather.wind}</span>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginTop: '8px', padding: '0 4px' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            <span style={{ fontSize: '10px', color: 'var(--text-dim)' }}>Last updated</span>
            <span style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>{weather.lastUpdated}</span>
          </div>
          <span 
            onClick={fetchWeather}
            style={{ 
              color: 'var(--text-dim)', 
              cursor: 'pointer',
              transform: isRefreshing ? 'rotate(180deg)' : 'rotate(0deg)',
              transition: 'transform 0.4s ease'
            }} 
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.92-10.44l5.58 5.58"/>
            </svg>
          </span>
        </div>
      </div>
    </aside>
  );
}