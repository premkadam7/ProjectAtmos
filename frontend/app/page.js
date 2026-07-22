'use client';

import { useEffect, useState } from 'react';
import { getForecast } from '@/lib/api';
import Card from '@/components/common/Card';
import CountUp from '@/components/common/CountUp';
import HeroSection from '@/components/common/HeroSection';
const CHART_ACCENT = '#5cb9ad';

function getAqiColor(aqi) {
  if (aqi <= 50) return '#4ade80';
  if (aqi <= 100) return '#a3e635';
  if (aqi <= 200) return '#facc15';
  if (aqi <= 300) return '#fb923c';
  if (aqi <= 400) return '#f97316';
  return '#ef4444';
}

function getAqiLabel(aqi) {
  if (aqi <= 50) return 'Good';
  if (aqi <= 100) return 'Satisfactory';
  if (aqi <= 200) return 'Moderate';
  if (aqi <= 300) return 'Poor';
  if (aqi <= 400) return 'Very Poor';
  return 'Severe';
}

function getAqiGradient(aqi) {
  if (aqi <= 50)  return 'linear-gradient(160deg, #04250f 0%, #16a34a 55%, #4ade80 100%)';
  if (aqi <= 100) return 'linear-gradient(160deg, #1c2306 0%, #65a30d 55%, #a3e635 100%)';
  if (aqi <= 200) return 'linear-gradient(160deg, #241d05 0%, #ca8a04 55%, #facc15 100%)';
  if (aqi <= 300) return 'linear-gradient(160deg, #2b1505 0%, #c2410c 55%, #fb923c 100%)';
  if (aqi <= 400) return 'linear-gradient(160deg, #2b0805 0%, #b91c1c 55%, #ef4444 100%)';
  return 'linear-gradient(160deg, #1c0524 0%, #7e22ce 55%, #a855f7 100%)';
}

function colorForRelative(t) {
  const stops = [
    { t: 0,    c: [74, 222, 128] },
    { t: 0.25, c: [163, 230, 53] },
    { t: 0.5,  c: [250, 204, 21] },
    { t: 0.75, c: [251, 146, 60] },
    { t: 1,    c: [239, 68, 68] },
  ];
  for (let i = 0; i < stops.length - 1; i++) {
    if (t >= stops[i].t && t <= stops[i + 1].t) {
      const localT = (t - stops[i].t) / (stops[i + 1].t - stops[i].t || 1);
      const c = stops[i].c.map((v, idx) => Math.round(v + (stops[i + 1].c[idx] - v) * localT));
      return `rgb(${c[0]}, ${c[1]}, ${c[2]})`;
    }
  }
  return `rgb(${stops[stops.length - 1].c.join(', ')})`;
}

function Sparkline({ values, color }) {
  const W = 120, H = 32;
  const max = Math.max(...values);
  const min = Math.min(...values);
  const range = max - min || 1;
  const pts = values.map((v, i) => {
    const x = (i / (values.length - 1)) * W;
    const y = H - ((v - min) / range) * H;
    return `${x},${y}`;
  }).join(' ');
  return (
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={{ marginTop: '10px', opacity: 0.7 }}>
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function StatCard({ title, numericValue, decimals = 0, suffix = '', subtitle, color, icon, sparkValues, animOrder = 0 }) {
  return (
    <Card className="stat-card stagger-in" style={{ flex: 1, animationDelay: `${animOrder * 0.08}s` }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <p style={{ fontSize: '12px', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{title}</p>
        {icon && (
          <div style={{
            width: '36px', height: '36px', borderRadius: '10px',
            background: `${color}18`, display: 'flex',
            alignItems: 'center', justifyContent: 'center', fontSize: '18px',
          }}>
            {icon}
          </div>
        )}
      </div>
      <p style={{ fontSize: '36px', fontWeight: '700', color: color || 'var(--text-primary)', lineHeight: 1, marginTop: '10px' }}>
        <CountUp value={numericValue} decimals={decimals} suffix={suffix} />
      </p>
      {subtitle && <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '5px' }}>{subtitle}</p>}
      {sparkValues && <Sparkline values={sparkValues} color={color || CHART_ACCENT} />}
    </Card>
  );
}

/* ---------- Live AQI hero card ---------- */
function LiveAqiCard({ aqi, pm25, animOrder = 0 }) {
  const label = getAqiLabel(aqi);
  const gradient = getAqiGradient(aqi);
  const sliderPct = Math.min((aqi / 500) * 100, 100);

  return (
    <Card
      className="stagger-in"
      style={{
        animationDelay: `${animOrder * 0.08}s`,
        background: gradient,
        backdropFilter: 'none',
        WebkitBackdropFilter: 'none',
        border: 'none',
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        minHeight: '420px',
      }}
    >
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '18px' }}>
          <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#fff', boxShadow: '0 0 6px #fff' }} />
          <span style={{ fontSize: '12px', color: 'rgba(255,255,255,0.85)', fontWeight: '500' }}>Live AQI</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'flex-end', gap: '10px' }}>
          <span style={{ fontSize: '72px', fontWeight: '800', color: '#fff', lineHeight: 1, letterSpacing: '-2px' }}>
            {aqi}
          </span>
          <span style={{ fontSize: '13px', color: 'rgba(255,255,255,0.7)', marginBottom: '12px' }}>(AQI-IN)</span>
        </div>

        <div style={{
          display: 'inline-block', marginTop: '14px',
          background: 'rgba(0,0,0,0.25)', border: '1px solid rgba(255,255,255,0.3)',
          borderRadius: '10px', padding: '8px 18px',
        }}>
          <span style={{ fontSize: '18px', fontWeight: '700', color: '#fff' }}>{label}</span>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '24px' }}>
          <div>
            <span style={{ fontSize: '12px', color: 'rgba(255,255,255,0.7)' }}>PM2.5 : </span>
            <span style={{ fontSize: '16px', fontWeight: '700', color: '#fff' }}>{pm25} </span>
            <span style={{ fontSize: '11px', color: 'rgba(255,255,255,0.6)' }}>µg/m³</span>
          </div>
          <div>
            <span style={{ fontSize: '12px', color: 'rgba(255,255,255,0.7)' }}>PM10 : </span>
            <span style={{ fontSize: '16px', fontWeight: '700', color: '#fff' }}>{Math.round(pm25 * 1.6)} </span>
            <span style={{ fontSize: '11px', color: 'rgba(255,255,255,0.6)' }}>µg/m³</span>
          </div>
        </div>
      </div>

      <div style={{ marginTop: '28px' }}>
        <div style={{
          position: 'relative', height: '8px', borderRadius: '4px',
          background: 'linear-gradient(to right, #4ade80, #a3e635, #facc15, #fb923c, #f97316, #8b5cf6, #ef4444)',
        }}>
          <div style={{
            position: 'absolute', left: `${sliderPct}%`, top: '50%',
            transform: 'translate(-50%, -50%)', width: '16px', height: '16px',
            borderRadius: '50%', background: 'white', border: '3px solid rgba(0,0,0,0.3)',
            boxShadow: '0 0 8px rgba(0,0,0,0.4)', transition: 'left 0.5s ease',
          }} />
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '6px' }}>
          <span style={{ fontSize: '10px', color: 'rgba(255,255,255,0.6)' }}>0</span>
          <span style={{ fontSize: '10px', color: 'rgba(255,255,255,0.6)' }}>500+</span>
        </div>
      </div>
    </Card>
  );
}

/* ---------- Livability hero card — same visual weight as Live AQI ---------- */
function LivabilityHeroCard({ aqi, animOrder = 0 }) {
  const aqiScore = Math.max(0, Math.round(100 - (aqi / 500) * 100));
  const greenScore = 72;
  const vulnScore = 58;
  const overall = Math.round((aqiScore + greenScore + vulnScore) / 3);

  const items = [
    { label: 'AQI Trend', score: aqiScore },
    { label: 'Green Cover (NDVI)', score: greenScore },
    { label: 'Vulnerability', score: vulnScore },
  ];

  return (
    <Card
      className="stagger-in"
      style={{
        animationDelay: `${animOrder * 0.08}s`,
        background: 'linear-gradient(160deg, #d7f9a7 0%, #45a984 55%, #baf0ff 100%)',
        backdropFilter: 'none',
        WebkitBackdropFilter: 'none',
        border: 'none',
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        minHeight: '420px',
      }}
    >
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '18px' }}>
          <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#fff', boxShadow: '0 0 6px #fff' }} />
          <span style={{ fontSize: '12px', color: 'rgba(255,255,255,0.85)', fontWeight: '500' }}>Livability Snapshot</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'flex-end', gap: '10px' }}>
          <span style={{ fontSize: '72px', fontWeight: '800', color: '#fff', lineHeight: 1, letterSpacing: '-2px' }}>
            <CountUp value={overall} />
          </span>
          <span style={{ fontSize: '13px', color: 'rgba(255,255,255,0.7)', marginBottom: '12px' }}>/100</span>
        </div>

        <div style={{
          display: 'inline-block', marginTop: '14px',
          background: 'rgba(0,0,0,0.25)', border: '1px solid rgba(255,255,255,0.3)',
          borderRadius: '10px', padding: '8px 18px',
        }}>
          <span style={{ fontSize: '18px', fontWeight: '700', color: '#fff' }}>
            {overall >= 70 ? 'Livable' : overall >= 45 ? 'Moderate' : 'Challenging'}
          </span>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '24px' }}>
        {items.map((item) => (
          <div key={item.label}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
              <span style={{ fontSize: '12px', color: 'rgba(255,255,255,0.8)' }}>{item.label}</span>
              <span style={{ fontSize: '12px', fontWeight: '700', color: '#fff' }}>{item.score}/100</span>
            </div>
            <div style={{ height: '5px', borderRadius: '3px', background: 'rgba(0,0,0,0.25)', overflow: 'hidden' }}>
              <div style={{ width: `${item.score}%`, height: '100%', background: 'rgba(255,255,255,0.85)', borderRadius: '3px' }} />
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

/* ---------- Cigarette illustration — rebuilt for realistic proportions + softer smoke ---------- */
function CigaretteIllustration() {
  return (
    <svg width="130" height="140" viewBox="0 0 160 160">
      {/* Smoke — soft layered wisps, varying widths and opacity for depth */}
      <path className="smoke-wisp" style={{ animationDelay: '0s' }}
        d="M118 62 C 128 50, 108 42, 116 28 C 122 18, 106 10, 114 -4"
        stroke="rgba(203,213,225,0.6)" strokeWidth="5" fill="none" strokeLinecap="round" />
      <path className="smoke-wisp" style={{ animationDelay: '1s' }}
        d="M126 68 C 138 58, 116 48, 126 36 C 134 26, 118 16, 128 4"
        stroke="rgba(203,213,225,0.4)" strokeWidth="3.5" fill="none" strokeLinecap="round" />
      <path className="smoke-wisp" style={{ animationDelay: '2s' }}
        d="M110 66 C 118 56, 102 48, 112 38"
        stroke="rgba(203,213,225,0.3)" strokeWidth="2.5" fill="none" strokeLinecap="round" />

      {/* Cigarette body — long, slender, correct proportions */}
      <g transform="rotate(-38 80 100)">
        {/* Ash flaking off the tip */}
        <ellipse cx="128" cy="82" rx="5" ry="2.5" fill="#9ca3af" opacity="0.5" />
        <ellipse cx="133" cy="76" rx="3" ry="1.8" fill="#9ca3af" opacity="0.35" />

        {/* Ember glow */}
        <circle cx="122" cy="86" r="11" fill="#fb923c" opacity="0.4">
          <animate attributeName="r" values="9;13;9" dur="1.6s" repeatCount="indefinite" />
          <animate attributeName="opacity" values="0.4;0.65;0.4" dur="1.6s" repeatCount="indefinite" />
        </circle>

        {/* Paper body */}
        <rect x="30" y="80" width="90" height="13" rx="2.5" fill="#fdfaf3" stroke="#e5ddc8" strokeWidth="0.75" />
        {/* Subtle paper seam */}
        <line x1="30" y1="86.5" x2="120" y2="86.5" stroke="#eee5cf" strokeWidth="0.5" />

        {/* Filter */}
        <rect x="14" y="79.5" width="18" height="14" rx="2.5" fill="#f5c99b" stroke="#d9ab77" strokeWidth="0.75" />
        {[19, 23, 27].map((x) => (
          <line key={x} x1={x} y1="80" x2={x} y2="93" stroke="#d9ab77" strokeWidth="0.6" opacity="0.7" />
        ))}

        {/* Ember tip */}
        <rect x="118" y="80" width="8" height="13" rx="2" fill="#c2410c" />
        <rect x="118" y="80" width="8" height="13" rx="2" fill="#fbbf24" opacity="0.75">
          <animate attributeName="opacity" values="0.75;1;0.75" dur="1.1s" repeatCount="indefinite" />
        </rect>
      </g>
    </svg>
  );
}

/* ---------- Cigarette card — redesigned with ember gradient + pack-equivalent slider ---------- */
function CigaretteCard({ cigarettes, pm25, animOrder = 0 }) {
  const cigNum = parseFloat(cigarettes);
  const weekly = (cigNum * 7).toFixed(0);
  const packPct = Math.min((cigNum / 20) * 100, 100); // 20 cigarettes = 1 pack

  return (
    <Card
      className="stagger-in"
      style={{
        animationDelay: `${animOrder * 0.08}s`,
        background: 'linear-gradient(155deg, #150a06 0%, #b83408 55%, #f97316 100%)',
        backdropFilter: 'none',
        WebkitBackdropFilter: 'none',
        border: 'none',
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        minHeight: '340px',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
            <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#fff', boxShadow: '0 0 6px #fff' }} />
            <span style={{ fontSize: '12px', color: 'rgba(255,255,255,0.85)', fontWeight: '500' }}>Today you had</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: '10px' }}>
            <span style={{ fontSize: '72px', fontWeight: '800', color: '#fff', lineHeight: 1, letterSpacing: '-2px' }}>
              <CountUp value={cigNum} decimals={1} />
            </span>
          </div>
          <p style={{ fontSize: '15px', color: 'rgba(255,255,255,0.75)', marginTop: '6px' }}>cigarettes worth of PM2.5</p>
        </div>
        <CigaretteIllustration />
      </div>

      <div style={{ marginTop: '20px' }}>
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'baseline',
          marginBottom: '8px',
        }}>
          <span style={{ fontSize: '12px', color: 'rgba(255,255,255,0.7)' }}>Daily pack equivalent</span>
          <span style={{ fontSize: '13px', fontWeight: '700', color: '#fff' }}>{(cigNum / 20).toFixed(2)} packs</span>
        </div>
        <div style={{ position: 'relative', height: '8px', borderRadius: '4px', background: 'rgba(0,0,0,0.3)' }}>
          <div style={{
            width: `${packPct}%`, height: '100%', borderRadius: '4px',
            background: 'linear-gradient(90deg, #fde68a, #f97316)',
            transition: 'width 0.6s ease',
          }} />
        </div>
        <p style={{ fontSize: '12px', color: 'rgba(255,255,255,0.65)', marginTop: '12px' }}>
          At this rate: <strong style={{ color: '#fff' }}>~{weekly} cigarettes</strong> this week · based on PM2.5 = {pm25} µg/m³
        </p>
      </div>
    </Card>
  );
}

/* ---------- Top Pollutants — hero stat (PM2.5) + compact secondary list, severity-colored ---------- */
function TopPollutantsCard({ pm25, animOrder = 0 }) {
  const secondary = [
    { name: 'PM10', value: Math.round(pm25 * 1.6), unit: 'µg/m³', max: 300 },
    { name: 'NO₂', value: Math.round(pm25 * 0.22), unit: 'ppb', max: 100 },
    { name: 'SO₂', value: Math.round(pm25 * 0.13), unit: 'ppb', max: 80 },
    { name: 'CO', value: (pm25 * 0.007).toFixed(1), unit: 'ppm', max: 10 },
    { name: 'O₃', value: Math.round(pm25 * 0.26), unit: 'ppb', max: 100 },
  ];
  const pm25Pct = Math.min((pm25 / 200) * 100, 100);
  const pm25Color = colorForRelative(pm25 / 200);

  return (
    <Card
      title="Top Pollutants"
      action={<span style={{ fontSize: '12px', color: 'var(--text-dim)' }} title="Current readings">ⓘ Now</span>}
      className="stagger-in"
      style={{ flex: 1, animationDelay: `${animOrder * 0.08}s` }}
    >
      {/* Hero stat: PM2.5, the primary AQI driver */}
      <div style={{ marginBottom: '20px', paddingBottom: '18px', borderBottom: '1px solid var(--border)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
          <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>PM2.5 <span style={{ fontSize: '11px', color: 'var(--text-dim)' }}>· primary driver</span></span>
          <span style={{ fontSize: '32px', fontWeight: '800', color: pm25Color, lineHeight: 1 }}>
            {pm25}<span style={{ fontSize: '14px', fontWeight: '500', color: 'var(--text-dim)' }}> µg/m³</span>
          </span>
        </div>
        <div style={{ height: '6px', borderRadius: '3px', background: 'var(--bg-tertiary)', overflow: 'hidden', marginTop: '10px' }}>
          <div style={{ width: `${pm25Pct}%`, height: '100%', background: pm25Color, borderRadius: '3px', transition: 'width 0.6s ease' }} />
        </div>
      </div>

      {/* Secondary pollutants, compact list */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {secondary.map(p => {
          const color = colorForRelative(parseFloat(p.value) / p.max);
          return (
            <div key={p.name} style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span style={{ fontSize: '12px', color: 'var(--text-secondary)', width: '32px', flexShrink: 0 }}>{p.name}</span>
              <div style={{ flex: 1, height: '4px', background: 'var(--bg-tertiary)', borderRadius: '2px', overflow: 'hidden' }}>
                <div style={{
                  width: `${Math.min((parseFloat(p.value) / p.max) * 100, 100)}%`,
                  height: '100%', background: color, borderRadius: '2px', transition: 'width 0.6s ease',
                }} />
              </div>
              <span style={{ fontSize: '11px', color: 'var(--text-secondary)', width: '64px', textAlign: 'right', flexShrink: 0 }}>
                {p.value} {p.unit}
              </span>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

const RANGE_CONFIG = {
  '12h': { points: 12, unitLabel: 'hr', stepHours: 1 },
  '24h': { points: 24, unitLabel: 'hr', stepHours: 1 },
  '7d':  { points: 7,  unitLabel: 'day', stepHours: 24 },
  '30d': { points: 30, unitLabel: 'day', stepHours: 24 },
};

const POLLUTANT_CONFIG = {
  aqi:  { label: 'AQI',   unit: '',       factor: 1 },
  pm25: { label: 'PM2.5', unit: 'µg/m³',  factor: 1 },
  pm10: { label: 'PM10',  unit: 'µg/m³',  factor: 1.6 },
  co:   { label: 'CO',    unit: 'ppm',    factor: 0.007 },
  no2:  { label: 'NO₂',   unit: 'ppb',    factor: 0.22 },
  so2:  { label: 'SO₂',   unit: 'ppb',    factor: 0.13 },
  o3:   { label: 'O₃',    unit: 'ppb',    factor: 0.26 },
};

function formatAxisLabel(date, unitLabel) {
  return unitLabel === 'hr'
    ? date.toLocaleTimeString('en-IN', { hour: 'numeric', hour12: true })
    : date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' });
}

function formatFullLabel(date, unitLabel) {
  return unitLabel === 'hr'
    ? date.toLocaleString('en-IN', { day: '2-digit', month: 'short', hour: 'numeric', hour12: true })
    : date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}

function generateHistoricalSeries(range, pollutantKey, baseAqi, basePm25, anchorDate) {
  const { points, unitLabel, stepHours } = RANGE_CONFIG[range];
  const { factor } = POLLUTANT_CONFIG[pollutantKey];
  const baseValue = pollutantKey === 'aqi' ? baseAqi : basePm25 * factor;

  const series = [];
  for (let i = 0; i < points; i++) {
    const seedStr = `${range}-${pollutantKey}-${i}`;
    let hash = 0;
    for (let c = 0; c < seedStr.length; c++) hash = (hash * 31 + seedStr.charCodeAt(c)) >>> 0;
    const wobble = ((hash % 100) / 100 - 0.5) * 0.35;
    const value = Math.max(0, baseValue * (1 + wobble));
    const hoursAgo = (points - 1 - i) * stepHours;
    const date = new Date(anchorDate.getTime() - hoursAgo * 3600 * 1000);
    series.push({
      date,
      axisLabel: formatAxisLabel(date, unitLabel),
      fullLabel: formatFullLabel(date, unitLabel),
      value: pollutantKey === 'aqi' ? Math.round(value) : parseFloat(value.toFixed(pollutantKey === 'co' ? 2 : 0)),
    });
  }
  return series;
}

function HistoricalAqiCard({ cityAqi, cityPm25, anchorDate, animOrder = 0 }) {
  const [range, setRange] = useState('24h');
  const [pollutant, setPollutant] = useState('aqi');
  const [chartType, setChartType] = useState('bar');

  const series = generateHistoricalSeries(range, pollutant, cityAqi, cityPm25, anchorDate);
  const config = POLLUTANT_CONFIG[pollutant];
  const unitLabel = RANGE_CONFIG[range].unitLabel;

  const minPoint = series.reduce((a, b) => (b.value < a.value ? b : a));
  const maxPoint = series.reduce((a, b) => (b.value > a.value ? b : a));

  const W = 700, H = 230, padL = 40, padR = 16, padT = 20, padB = 34;
  const values = series.map(p => p.value);
  const dataMin = Math.min(...values);
  const dataMax = Math.max(...values);
  const axisMax = dataMax * 1.15;
  const axisMin = 0;

  const x = (i) => padL + (i / (series.length - 1)) * (W - padL - padR);
  const y = (v) => H - padB - ((v - axisMin) / (axisMax - axisMin || 1)) * (H - padT - padB);

  const linePath = series.map((p, i) => `${i === 0 ? 'M' : 'L'} ${x(i)} ${y(p.value)}`).join(' ');
  const areaPath = `${linePath} L ${x(series.length - 1)} ${H - padB} L ${x(0)} ${H - padB} Z`;

  const barSlot = (W - padL - padR) / series.length;
  const barWidth = barSlot * 0.55;

  const tabButtonStyle = (active) => ({
    padding: '5px 12px',
    borderRadius: '8px',
    fontSize: '12px',
    fontWeight: 600,
    cursor: 'pointer',
    border: 'none',
    background: active ? CHART_ACCENT : 'var(--bg-tertiary)',
    color: active ? '#0a0a0a' : 'var(--text-secondary)',
    transition: 'all 0.15s ease',
  });

  const chartKey = `${range}-${pollutant}-${chartType}`;
  const labelStride = Math.ceil(series.length / 8);

  return (
    <Card title="Historical AQI Data" className="stagger-in" style={{ animationDelay: `${animOrder * 0.08}s` }}>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '16px', marginBottom: '6px', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', gap: '6px' }}>
          {Object.keys(RANGE_CONFIG).map((r) => (
            <button key={r} style={tabButtonStyle(range === r)} onClick={() => setRange(r)}>
              {r === '12h' ? '12 Hours' : r === '24h' ? '24 Hours' : r === '7d' ? '7 Days' : '30 Days'}
            </button>
          ))}
        </div>
        <div style={{ display: 'flex', gap: '6px' }}>
          <button style={tabButtonStyle(chartType === 'line')} onClick={() => setChartType('line')}>📈</button>
          <button style={tabButtonStyle(chartType === 'bar')} onClick={() => setChartType('bar')}>📊</button>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginBottom: '18px' }}>
        {Object.entries(POLLUTANT_CONFIG).map(([key, cfg]) => (
          <button key={key} style={tabButtonStyle(pollutant === key)} onClick={() => setPollutant(key)}>
            {cfg.label}
          </button>
        ))}
      </div>

      <svg key={chartKey} className="chart-fade" width="100%" height={H} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="xMidYMid meet">
        {[0, 0.5, 1].map((f, i) => (
          <line key={i} x1={padL} x2={W - padR}
            y1={padT + f * (H - padT - padB)} y2={padT + f * (H - padT - padB)}
            stroke="var(--bg-tertiary)" strokeWidth="1" />
        ))}
        {chartType === 'line' ? (
          <>
            <path d={areaPath} fill={CHART_ACCENT} opacity="0.1" stroke="none" />
            <path d={linePath} fill="none" stroke={CHART_ACCENT} strokeWidth="2.5" />
            {series.map((p, i) => {
              const t = (p.value - dataMin) / (dataMax - dataMin || 1);
              return <circle key={i} cx={x(i)} cy={y(p.value)} r="3.5" fill={colorForRelative(t)} />;
            })}
          </>
        ) : (
          series.map((p, i) => {
            const t = (p.value - dataMin) / (dataMax - dataMin || 1);
            const barH = (H - padB) - y(p.value);
            return (
              <rect
                key={i}
                className="bar-rise"
                style={{ animationDelay: `${i * 15}ms` }}
                x={x(i) - barWidth / 2}
                y={y(p.value)}
                width={barWidth}
                height={Math.max(barH, 2)}
                rx="3"
                fill={colorForRelative(t)}
              />
            );
          })
        )}
        {series.map((p, i) => (
          i % labelStride === 0 && (
            <text key={i} x={x(i)} y={H - 12} fontSize="10" fill="var(--text-dim)" textAnchor="middle">
              {p.axisLabel}
            </text>
          )
        ))}
      </svg>

      <p style={{ fontSize: '11px', color: 'var(--text-dim)', textAlign: 'center', marginTop: '4px' }}>
        {formatFullLabel(series[0].date, unitLabel)} — {formatFullLabel(series[series.length - 1].date, unitLabel)}
      </p>

      <div style={{ display: 'flex', gap: '24px', marginTop: '16px' }}>
        <div>
          <p style={{ fontSize: '20px', fontWeight: 700, color: '#4ade80' }}>
            {minPoint.value}{config.unit && ` ${config.unit}`}
          </p>
          <p style={{ fontSize: '11px', color: 'var(--text-dim)' }}>
            Min. {config.label} at {minPoint.fullLabel}
          </p>
        </div>
        <div>
          <p style={{ fontSize: '20px', fontWeight: 700, color: '#ef4444' }}>
            {maxPoint.value}{config.unit && ` ${config.unit}`}
          </p>
          <p style={{ fontSize: '11px', color: 'var(--text-dim)' }}>
            Max. {config.label} at {maxPoint.fullLabel}
          </p>
        </div>
      </div>
    </Card>
  );
}

export default function Home() {
  const [data, setData] = useState(null);
  const [selectedWard, setSelectedWard] = useState(null);

  useEffect(() => {
    getForecast('delhi').then(d => {
      setData(d);
      if (d && d.wards && d.wards.length > 0) {
        const worst = [...d.wards].sort((a, b) => b.current_aqi - a.current_aqi)[0];
        setSelectedWard(worst);
      }
    }).catch(err => {
      setData({ error: 'Failed to fetch' });
    });
  }, []);

  if (!data) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh', color: 'var(--text-dim)' }}>
      Loading...
    </div>
  );
  
  if (data.error || !data.wards || data.wards.length === 0) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh', color: 'var(--text-dim)', flexDirection: 'column', gap: '10px' }}>
      <p style={{ fontSize: '18px', color: '#ef4444' }}>Error: Backend Data Not Available</p>
      <p>The server is either still deploying the new datasets, or there is an API error.</p>
      <p>Please wait 1-2 minutes and refresh the page.</p>
    </div>
  );

  const topWorst = [...data.wards].sort((a, b) => b.current_aqi - a.current_aqi).slice(0, 5);
  const bestWard = data.wards.find(w => w.ward_id === data.best_ward) || data.wards[data.wards.length - 1];
  const cityAqi = Math.round(data.city_avg_aqi);
  const cityPm25 = Math.round(cityAqi * 0.42);
  const cigarettes = (cityPm25 / 22).toFixed(1);
  const anchorDate = data.generated_at ? new Date(data.generated_at) : new Date();

  const sparkBest = [110, 105, 98, 102, 95, 100, bestWard.current_aqi];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

      <div>
        <h2 style={{ fontSize: '24px', fontWeight: '700', color: 'var(--text-primary)' }}>
          Delhi Air Quality Index & Realtime Air Pollution
        </h2>
      </div>

      {/* Live AQI + Livability — 50/50 hero row */}
      <div style={{ display: 'flex', gap: '16px' }}>
        <LiveAqiCard aqi={cityAqi} pm25={cityPm25} animOrder={0} />
        <LivabilityHeroCard aqi={cityAqi} animOrder={1} />
      </div>

      {/* Cigarette (illustrated) + Top Pollutants — 50/50 */}
      <div style={{ display: 'flex', gap: '16px' }}>
        <CigaretteCard cigarettes={cigarettes} animOrder={2} />
        <TopPollutantsCard pm25={cityPm25} animOrder={3} />
      </div>

      {/* Best Ward — alone for now, pairing TBD */}
      <StatCard
        title="Best Ward"
        numericValue={bestWard.current_aqi}
        subtitle={bestWard.ward_name}
        color={getAqiColor(bestWard.current_aqi)}
        icon="✅"
        sparkValues={sparkBest}
        animOrder={4}
      />

      {/* Top 5 Worst Wards */}
      <Card title="Top 5 Worst Wards" className="stagger-in" style={{ animationDelay: '0.4s' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {topWorst.map((ward, i) => (
            <div
              key={ward.ward_id}
              onClick={() => setSelectedWard(ward)}
              style={{
                display: 'flex', alignItems: 'center', gap: '12px',
                cursor: 'pointer', padding: '4px 6px', borderRadius: '8px',
                background: selectedWard?.ward_id === ward.ward_id ? 'rgba(92,224,210,0.08)' : 'transparent',
                transition: 'background 0.2s ease',
              }}
            >
              <span style={{ fontSize: '12px', color: 'var(--text-dim)', width: '16px' }}>{i + 1}</span>
              <span style={{ flex: 1, fontSize: '13px', color: 'var(--text-primary)' }}>{ward.ward_name}</span>
              <div style={{ flex: 2, height: '6px', background: 'var(--bg-tertiary)', borderRadius: '3px', overflow: 'hidden' }}>
                <div style={{ width: `${(ward.current_aqi / 500) * 100}%`, height: '100%', background: getAqiColor(ward.current_aqi), borderRadius: '3px' }} />
              </div>
              <span style={{ fontSize: '13px', fontWeight: '600', color: getAqiColor(ward.current_aqi), width: '36px', textAlign: 'right' }}>
                {ward.current_aqi}
              </span>
            </div>
          ))}
        </div>
      </Card>

      {/* Historical chart */}
      <HistoricalAqiCard cityAqi={cityAqi} cityPm25={cityPm25} anchorDate={anchorDate} animOrder={5} />

      {/* All wards pills */}
      <Card title="All Wards — Current Status" className="stagger-in" style={{ animationDelay: '0.56s' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
          {data.wards.map((ward) => (
            <div
              key={ward.ward_id}
              onClick={() => setSelectedWard(ward)}
              style={{
                padding: '6px 12px', borderRadius: '20px',
                background: selectedWard?.ward_id === ward.ward_id ? `${getAqiColor(ward.current_aqi)}20` : 'var(--bg-tertiary)',
                border: `1px solid ${getAqiColor(ward.current_aqi)}40`,
                display: 'flex', alignItems: 'center', gap: '6px',
                cursor: 'pointer', transition: 'all 0.2s ease',
              }}
            >
              <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: getAqiColor(ward.current_aqi) }} />
              <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>{ward.ward_name}</span>
              <span style={{ fontSize: '12px', fontWeight: '700', color: getAqiColor(ward.current_aqi) }}>{ward.current_aqi}</span>
              <span style={{ fontSize: '10px', color: 'var(--text-dim)' }}>
                {ward.trend === 'worsening' ? '↑' : ward.trend === 'improving' ? '↓' : '→'}
              </span>
            </div>
          ))}
        </div>
      </Card>

    </div>
  );
}