'use client';

import Mascot from './Mascot';

/* ================================================================
   HERO SECTION — replaces the old <LiveAqiCard /> + <LivabilityHeroCard />
   50/50 row in app/page.js. One full-bleed magazine hero instead of
   two boxed cards.

   Drop this file in components/common/HeroSection.js, then in
   app/page.js:

     import HeroSection from '@/components/common/HeroSection';
     ...
     <HeroSection aqi={cityAqi} pm25={cityPm25} animOrder={0} />

   ...replacing the block that currently renders:
     <div style={{ display: 'flex', gap: '16px' }}>
       <LiveAqiCard .../>
       <LivabilityHeroCard .../>
     </div>
================================================================ */

function getAqiLabel(aqi) {
  if (aqi <= 50) return 'Good';
  if (aqi <= 100) return 'Satisfactory';
  if (aqi <= 200) return 'Moderate';
  if (aqi <= 300) return 'Poor';
  if (aqi <= 400) return 'Very Poor';
  return 'Severe';
}

function getAqiColor(aqi) {
  if (aqi <= 50) return '#4ade80';
  if (aqi <= 100) return '#a3e635';
  if (aqi <= 200) return '#facc15';
  if (aqi <= 300) return '#fb923c';
  if (aqi <= 400) return '#f97316';
  return '#ff8f6b';
}

export default function HeroSection({ aqi, pm25, greenScore = 72, vulnScore = 58, animOrder = 0 }) {
  const color = getAqiColor(aqi);
  const label = getAqiLabel(aqi);
  const livability = Math.max(0, Math.round((Math.round(100 - (aqi / 500) * 100) + greenScore + vulnScore) / 3));

  return (
    <div
      className="hero-magazine stagger-in"
      style={{ animationDelay: `${animOrder * 0.08}s` }}
    >
      <div className="hero-blob b1" />
      <div className="hero-blob b2" />
      <div className="hero-blob b3" />

      {/* left: the number */}
      <div style={{ position: 'relative', zIndex: 1 }}>
        <span className="hero-eyebrow">
          <span style={{ width: 7, height: 7, borderRadius: '50%', background: color, display: 'inline-block', boxShadow: `0 0 8px ${color}` }} />
          Live right now
        </span>

        <div className="hero-number">
          {aqi}
          <span
            className="hero-number-underline"
            style={{ background: color }}
          />
        </div>

        <div className="hero-label-pill" style={{ background: color }}>
          {label}
        </div>

        <div className="hero-subrow">
          <div className="hero-mini-stat">PM2.5 &nbsp;<b>{pm25} µg/m³</b></div>
          <div className="hero-mini-stat">PM10 &nbsp;<b>{Math.round(pm25 * 1.6)} µg/m³</b></div>
          <div className="hero-mini-stat">Livability &nbsp;<b>{livability}/100</b></div>
        </div>
      </div>

      {/* right: mascot */}
      <div style={{ position: 'relative', zIndex: 1, flexShrink: 0 }}>
        <Mascot aqi={aqi} size={190} />
      </div>
    </div>
  );
}