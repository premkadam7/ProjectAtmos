'use client';

import { useEffect, useRef, useState } from 'react';
import ThemeToggle from '@/components/ThemeToggle';

export default function TopBar() {
  const [hidden, setHidden] = useState(false);
  const lastScrollY = useRef(0);

  useEffect(() => {
    lastScrollY.current = window.scrollY;

    function handleScroll() {
      const currentScrollY = window.scrollY;
      const scrolledDown = currentScrollY > lastScrollY.current;
      const scrolledEnough = Math.abs(currentScrollY - lastScrollY.current) > 4;

      // Always show near the top of the page, regardless of direction
      if (currentScrollY < 60) {
        setHidden(false);
      } else if (scrolledEnough) {
        setHidden(scrolledDown);
      }

      lastScrollY.current = currentScrollY;
    }

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <header
      className="top-bar"
      style={{
        position: 'sticky',
        top: 0,
        zIndex: 50,
        transform: hidden ? 'translateY(-100%)' : 'translateY(0)',
        transition: 'transform 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
        willChange: 'transform',
      }}
    >
      <div className="greeting">
        <h2 className="greeting-title">
          <span className="greeting-word">Namaste</span>
          <span className="greeting-city">Delhi</span>
        </h2>
      </div>

      <div className="top-bar-actions">
        <div className="search-wrapper">
          <span className="search-icon">🔍</span>
          <input
            type="text"
            className="search-bar"
            placeholder="Search location, society or area..."
          />
        </div>

        <ThemeToggle />
      </div>
    </header>
  );
}