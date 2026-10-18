'use client';

import { useEffect, useSyncExternalStore } from 'react';

const listeners = new Set();

function subscribe(callback) {
  listeners.add(callback);
  return () => listeners.delete(callback);
}

function getSnapshot() {
  try {
    return localStorage.getItem('atmos-theme') !== 'light';
  } catch {
    return true;
  }
}

// Server render (and hydration) assumes dark, matching the default theme
function getServerSnapshot() {
  return true;
}

export default function ThemeToggle() {
  const isDark = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  useEffect(() => {
    document.documentElement.classList.toggle('light', !isDark);
  }, [isDark]);

  const toggle = () => {
    try {
      localStorage.setItem('atmos-theme', isDark ? 'light' : 'dark');
    } catch {}
    listeners.forEach((l) => l());
  };

  return (
    <button className="theme-toggle" onClick={toggle}>
      <span>{isDark ? '☀️' : '🌙'}</span>
      <span>{isDark ? 'Light' : 'Dark'}</span>
    </button>
  );
}
