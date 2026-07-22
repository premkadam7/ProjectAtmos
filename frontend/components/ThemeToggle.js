'use client';

import { useState, useEffect } from 'react';

export default function ThemeToggle() {
  const [isDark, setIsDark] = useState(true);

  useEffect(() => {
    const saved = localStorage.getItem('atmos-theme');
    if (saved === 'light') {
      setIsDark(false);
      document.documentElement.classList.add('light');
    } else {
      setIsDark(true);
      document.documentElement.classList.remove('light');
    }
  }, []);

  const toggle = () => {
    const newIsDark = !isDark;
    setIsDark(newIsDark);
    if (newIsDark) {
      document.documentElement.classList.remove('light');
      localStorage.setItem('atmos-theme', 'dark');
    } else {
      document.documentElement.classList.add('light');
      localStorage.setItem('atmos-theme', 'light');
    }
  };

  return (
    <button className="theme-toggle" onClick={toggle}>
      <span>{isDark ? '☀️' : '🌙'}</span>
      <span>{isDark ? 'Light' : 'Dark'}</span>
    </button>
  );
}