'use client';

import { useEffect, useMemo, useState } from 'react';
import dynamic from 'next/dynamic';
import { BASE_URL, getForecast, getTimeline, getHistory, getWardDetail } from '@/lib/api';
import { getAqiColor, getAqiLabel, SOURCE_INFO } from '@/lib/aqi';
import Card from '@/components/common/Card';
import CountUp from '@/components/common/CountUp';

const PredictionMap = dynamic(() => import('@/components/common/PredictionMap'), {
  ssr: false,
  loading: () => <div className="skeleton" style={{ height: 560, borderRadius: 20 }} />,
});

const CHART_ACCENT = '#5cb9ad';

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
  const v = Math.max(0, Math.min(1, t));
  for (let i = 0; i < stops.length - 1; i++) {
    if (v >= stops[i].t && v <= stops[i + 1].t) {
      const localT = (v - stops[i].t) / (stops[i + 1].t - stops[i].t || 1);
      const c = stops[i].c.map((x, idx) => Math.round(x + (stops[i + 1].c[idx] - x) * localT));
      return `rgb(${c[0]}, ${c[1]}, ${c[2]})`;
    }
  }
  return `rgb(${stops[stops.length - 1].c.join(', ')})`;
}

// Measure a container so SVG charts draw at real pixel width (text stays a constant size)
function useWidth(fallback = 640) {
  const [el, setEl] = useState(null);
  const [width, setWidth] = useState(fallback);
  useEffect(() => {
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => setWidth(Math.max(280, Math.round(entry.contentRect.width))));
    ro.observe(el);
    return () => ro.disconnect();
  }, [el]);
  return [setEl, width];
}

function Skeleton({ height = 200, style = {} }) {
  return <div className="skeleton" style={{ height, borderRadius: 16, ...style }} />;
}

function formatTime(iso, opts = { hour: 'numeric', minute: '2-digit', hour12: true }) {
  return new Date(iso).toLocaleString('en-IN', opts);
}

/* ---------- Data source badge ---------- */
function DataSourceBadge({ data }) {
  if (!data?.data_source) return null;
  const info = SOURCE_INFO[data.data_source] || SOURCE_INFO['offline-sample'];
  const observed = formatTime(data.observed_at, { day: '2-digit', month: 'short', hour: 'numeric', hour12: true });
  return (
    <div className="source-badge" title={data.source_detail} style={{ '--c': info.tone }}>
      <span className="source-dot" />
      <span className="source-label">{info.label}</span>
      <span className="source-meta">{data.source_detail} · observed {observed}</span>
    </div>
  );
}

/* ---------- Live AQI hero card ---------- */
function LiveAqiCard({ aqi, pm25, pm10, observedAt, animOrder = 0 }) {
  const label = getAqiLabel(aqi);
  const sliderPct = Math.min((aqi / 500) * 100, 100);

  return (
    <Card
      className="stagger-in"
      style={{
        animationDelay: `${animOrder * 0.08}s`,
        background: getAqiGradient(aqi),
        backdropFilter: 'none',
        WebkitBackdropFilter: 'none',
        border: 'none',
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        minHeight: '340px',
      }}
    >
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '18px' }}>
          <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#fff', boxShadow: '0 0 6px #fff' }} />
          <span style={{ fontSize: '12px', color: 'rgba(255,255,255,0.85)', fontWeight: '500' }}>
            Delhi average · {observedAt ? formatTime(observedAt) : 'now'}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'flex-end', gap: '10px' }}>
          <span style={{ fontSize: '72px', fontWeight: '800', color: '#fff', lineHeight: 1, letterSpacing: '-2px' }}>
            <CountUp value={aqi} />
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

        <div style={{ display: 'flex', gap: '28px', marginTop: '24px' }}>
          {[['PM2.5', pm25], ['PM10', pm10]].map(([name, v]) => (
            <div key={name}>
              <span style={{ fontSize: '12px', color: 'rgba(255,255,255,0.7)' }}>{name} </span>
              <span style={{ fontSize: '18px', fontWeight: '700', color: '#fff' }}>{v ?? '—'} </span>
              <span style={{ fontSize: '11px', color: 'rgba(255,255,255,0.6)' }}>µg/m³</span>
            </div>
          ))}
        </div>
      </div>

      <div style={{ marginTop: '28px' }}>
        <div style={{
          position: 'relative', height: '8px', borderRadius: '4px',
          background: 'linear-gradient(to right, #22c55e, #84cc16, #eab308, #f97316, #ef4444, #a21caf)',
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

/* ---------- 72h forecast chart for one ward (model median + 10–90% band) ---------- */
function ForecastCard({ ward, detail, animOrder = 0 }) {
  const [hover, setHover] = useState(null);
  const [boxRef, W] = useWidth();

  if (!detail?.hourly?.length) {
    return (
      <Card title="72-hour forecast" className="stagger-in" style={{ flex: 1.4, animationDelay: `${animOrder * 0.08}s` }}>
        <div ref={boxRef}><Skeleton height={250} /></div>
      </Card>
    );
  }

  const points = [
    { timestamp: detail.observed_at, aqi: detail.current_aqi, aqi_low: detail.current_aqi, aqi_high: detail.current_aqi },
    ...detail.hourly,
  ];
  const H = 220, padL = 34, padR = 10, padT = 12, padB = 26;
  const maxV = Math.max(...points.map((p) => p.aqi_high)) * 1.08;
  const minV = Math.max(0, Math.min(...points.map((p) => p.aqi_low)) * 0.9);
  const x = (i) => padL + (i / (points.length - 1)) * (W - padL - padR);
  const y = (v) => padT + (1 - (v - minV) / (maxV - minV || 1)) * (H - padT - padB);

  const line = points.map((p, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(p.aqi).toFixed(1)}`).join(' ');
  const band = [
    ...points.map((p, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(p.aqi_high).toFixed(1)}`),
    ...points.slice().reverse().map((p, j) => `L${x(points.length - 1 - j).toFixed(1)},${y(p.aqi_low).toFixed(1)}`),
    'Z',
  ].join(' ');

  // Colour the line by AQI band via a vertical gradient in chart coordinates
  const stops = [0, 50, 100, 200, 300, 400, 500]
    .map((v) => ({ v, off: Math.max(0, Math.min(1, (y(v) - padT) / (H - padT - padB))) }))
    .reverse();

  const forecast = detail.hourly;
  const peak = forecast.reduce((a, b) => (b.aqi > a.aqi ? b : a));
  const best = forecast.reduce((a, b) => (b.aqi < a.aqi ? b : a));
  const h = hover ?? null;
  const hp = h != null ? points[h] : null;
  const ticks = [0, 24, 48, 72];
  const gridVals = [minV, (minV + maxV) / 2, maxV];

  function onMove(e) {
    const rect = e.currentTarget.getBoundingClientRect();
    const px = ((e.clientX - rect.left) / rect.width) * W;
    const i = Math.round(((px - padL) / (W - padL - padR)) * (points.length - 1));
    setHover(Math.max(0, Math.min(points.length - 1, i)));
  }

  return (
    <Card
      title={`72-hour forecast · ${ward?.ward_name ?? ''}`}
      action={<span className="chip-muted">LightGBM · 10–90% band</span>}
      className="stagger-in"
      style={{ flex: 1.4, animationDelay: `${animOrder * 0.08}s` }}
    >
      <div ref={boxRef} style={{ position: 'relative' }}>
        <svg
          width="100%" height={H} viewBox={`0 0 ${W} ${H}`} style={{ display: 'block', cursor: 'crosshair' }}
          onMouseMove={onMove} onMouseLeave={() => setHover(null)}
        >
          <defs>
            <linearGradient id="fc-line" gradientUnits="userSpaceOnUse" x1="0" x2="0" y1={padT} y2={H - padB}>
              {stops.map((s) => <stop key={s.v} offset={s.off} stopColor={getAqiColor(s.v)} />)}
            </linearGradient>
          </defs>
          {gridVals.map((v, i) => (
            <g key={i}>
              <line x1={padL} x2={W - padR} y1={y(v)} y2={y(v)} stroke="var(--border)" strokeDasharray="3 4" />
              <text x={padL - 6} y={y(v) + 3} fontSize="10" textAnchor="end" fill="var(--text-dim)">{Math.round(v)}</text>
            </g>
          ))}
          <path d={band} fill="var(--accent-primary)" opacity="0.13" />
          <path d={line} fill="none" stroke="url(#fc-line)" strokeWidth="2.6" strokeLinejoin="round" />
          <circle cx={x(0)} cy={y(points[0].aqi)} r="4.5" fill={getAqiColor(points[0].aqi)} stroke="#fff" strokeWidth="2" />
          {ticks.map((t) => (
            <text key={t} x={x(t)} y={H - 8} fontSize="10" textAnchor={t === 0 ? 'start' : t === 72 ? 'end' : 'middle'} fill="var(--text-dim)">
              {t === 0 ? 'Now' : `+${t}h`}
            </text>
          ))}
          {hp && (
            <g>
              <line x1={x(h)} x2={x(h)} y1={padT} y2={H - padB} stroke="var(--text-dim)" strokeDasharray="2 3" />
              <circle cx={x(h)} cy={y(hp.aqi)} r="4" fill={getAqiColor(hp.aqi)} stroke="#fff" strokeWidth="1.5" />
            </g>
          )}
        </svg>
        {hp && (
          <div className="chart-tip" style={{ left: `${(x(h) / W) * 100}%` }}>
            <strong style={{ color: getAqiColor(hp.aqi) }}>{Math.round(hp.aqi)}</strong> {getAqiLabel(hp.aqi)}
            <span>{h === 0 ? 'Now' : formatTime(hp.timestamp, { weekday: 'short', hour: 'numeric', hour12: true })}</span>
            {h > 0 && <span>range {Math.round(hp.aqi_low)}–{Math.round(hp.aqi_high)}</span>}
          </div>
        )}
      </div>

      <div className="forecast-stats">
        <div>
          <p className="forecast-stat-value" style={{ color: getAqiColor(peak.aqi) }}>{Math.round(peak.aqi)}</p>
          <p className="forecast-stat-label">Peak · {formatTime(peak.timestamp, { weekday: 'short', hour: 'numeric', hour12: true })}</p>
        </div>
        <div>
          <p className="forecast-stat-value" style={{ color: getAqiColor(best.aqi) }}>{Math.round(best.aqi)}</p>
          <p className="forecast-stat-label">Cleanest · {formatTime(best.timestamp, { weekday: 'short', hour: 'numeric', hour12: true })}</p>
        </div>
        <div>
          <p className="forecast-stat-value" style={{ color: getAqiColor(forecast[23].aqi) }}>{Math.round(forecast[23].aqi)}</p>
          <p className="forecast-stat-label">Tomorrow, same time</p>
        </div>
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

/* ---------- Pollutants: latest measured values vs CPCB limits ---------- */
// CPCB National Ambient Air Quality Standards (24h, or 8h for CO/O3)
const POLLUTANTS = [
  { key: 'pm25', name: 'PM2.5', unit: 'µg/m³', limit: 60 },
  { key: 'pm10', name: 'PM10', unit: 'µg/m³', limit: 100 },
  { key: 'no2', name: 'NO₂', unit: 'µg/m³', limit: 80 },
  { key: 'so2', name: 'SO₂', unit: 'µg/m³', limit: 80 },
  { key: 'co', name: 'CO', unit: 'mg/m³', limit: 2, scale: 0.001 },
  { key: 'o3', name: 'O₃', unit: 'µg/m³', limit: 100 },
];

function TopPollutantsCard({ latest, animOrder = 0 }) {
  return (
    <Card
      title="Pollutants vs safe limit"
      action={<span className="chip-muted">CPCB standard</span>}
      className="stagger-in"
      style={{ flex: 1, animationDelay: `${animOrder * 0.08}s` }}
    >
      {!latest ? <Skeleton height={230} /> : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {POLLUTANTS.map((p) => {
            const value = latest[p.key] * (p.scale ?? 1);
            const ratio = value / p.limit;
            const color = colorForRelative(ratio / 3);
            return (
              <div key={p.key}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '5px' }}>
                  <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>{p.name}</span>
                  <span style={{ fontSize: '13px', color: 'var(--text-primary)', fontWeight: 600 }}>
                    {value.toFixed(p.scale ? 2 : 0)} <span style={{ color: 'var(--text-dim)', fontWeight: 400, fontSize: '11px' }}>{p.unit}</span>
                    <span style={{ color, fontWeight: 700, fontSize: '11px', marginLeft: '8px' }}>{ratio.toFixed(1)}×</span>
                  </span>
                </div>
                <div style={{ position: 'relative', height: '6px', background: 'var(--bg-tertiary)', borderRadius: '3px', overflow: 'hidden' }}>
                  <div style={{ width: `${Math.min(ratio / 3, 1) * 100}%`, height: '100%', background: color, borderRadius: '3px', transition: 'width 0.6s ease' }} />
                  {/* safe-limit marker at 1× */}
                  <div style={{ position: 'absolute', left: '33.3%', top: 0, bottom: 0, width: '2px', background: 'var(--text-dim)', opacity: 0.6 }} />
                </div>
              </div>
            );
          })}
          <p style={{ fontSize: '11px', color: 'var(--text-dim)' }}>Bar marker = safe limit (1×). Scale shows up to 3× the limit.</p>
        </div>
      )}
    </Card>
  );
}

/* ---------- Historical chart (measured) ---------- */
const RANGE_CONFIG = {
  '12h': { hours: 12, bucket: 1, label: '12 Hours' },
  '24h': { hours: 24, bucket: 1, label: '24 Hours' },
  '7d':  { hours: 24 * 7, bucket: 6, label: '7 Days' },
  '30d': { hours: 24 * 30, bucket: 24, label: '30 Days' },
};

const SERIES_CONFIG = {
  aqi:  { label: 'AQI',   unit: '' },
  pm25: { label: 'PM2.5', unit: 'µg/m³' },
  pm10: { label: 'PM10',  unit: 'µg/m³' },
  co:   { label: 'CO',    unit: 'mg/m³', scale: 0.001, digits: 2 },
  no2:  { label: 'NO₂',   unit: 'µg/m³' },
  so2:  { label: 'SO₂',   unit: 'µg/m³' },
  o3:   { label: 'O₃',    unit: 'µg/m³' },
};

function bucketSeries(series, hours, bucket, key) {
  if (!series?.length) return [];
  const end = new Date(series[series.length - 1].timestamp).getTime();
  const start = end - (hours - 1) * 3600 * 1000;
  const scale = SERIES_CONFIG[key].scale ?? 1;
  const buckets = new Map();
  series.forEach((p) => {
    const t = new Date(p.timestamp).getTime();
    if (t < start) return;
    const b = Math.floor((end - t) / (bucket * 3600 * 1000));
    const entry = buckets.get(b) || { sum: 0, n: 0, t };
    entry.sum += p[key] * scale;
    entry.n += 1;
    entry.t = Math.min(entry.t, t);
    buckets.set(b, entry);
  });
  return [...buckets.entries()]
    .sort((a, b) => b[0] - a[0])
    .map(([, e]) => ({ date: new Date(e.t), value: e.sum / e.n }));
}

function HistoricalCard({ history, animOrder = 0 }) {
  const [range, setRange] = useState('24h');
  const [key, setKey] = useState('aqi');
  const [chartType, setChartType] = useState('line');
  const cfg = SERIES_CONFIG[key];
  const { hours, bucket } = RANGE_CONFIG[range];
  const series = useMemo(() => bucketSeries(history?.series, hours, bucket, key), [history, hours, bucket, key]);
  const available = history?.series?.length ?? 0;

  const tab = (active) => ({
    padding: '5px 12px', borderRadius: '8px', fontSize: '12px', fontWeight: 600, cursor: 'pointer', border: 'none',
    background: active ? CHART_ACCENT : 'var(--bg-tertiary)', color: active ? '#0a0a0a' : 'var(--text-secondary)',
    transition: 'all 0.15s ease',
  });

  const fmt = (v) => (cfg.digits ? v.toFixed(cfg.digits) : Math.round(v));
  const dayLabels = bucket >= 24;
  const axisLabel = (d) => (dayLabels
    ? d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })
    : d.toLocaleString('en-IN', { hour: 'numeric', hour12: true, ...(bucket > 1 ? { day: '2-digit', month: 'short' } : {}) }));
  const fullLabel = (d) => d.toLocaleString('en-IN', { day: '2-digit', month: 'short', hour: 'numeric', hour12: true });

  return (
    <Card
      title="Historical air quality"
      action={<span className="chip-muted">{history?.data_source === 'live' ? 'Ground-calibrated' : 'Measured'}</span>}
      className="stagger-in"
      style={{ animationDelay: `${animOrder * 0.08}s` }}
    >
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', marginBottom: '10px', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
          {Object.entries(RANGE_CONFIG).map(([r, c]) => (
            <button key={r} style={{ ...tab(range === r), opacity: available && available < c.hours / 2 ? 0.5 : 1 }}
              onClick={() => setRange(r)} title={available < c.hours ? `Only ${Math.round(available / 24)} days of history available` : undefined}>
              {c.label}
            </button>
          ))}
        </div>
        <div style={{ display: 'flex', gap: '6px' }}>
          <button style={tab(chartType === 'line')} onClick={() => setChartType('line')} aria-label="Line chart">📈</button>
          <button style={tab(chartType === 'bar')} onClick={() => setChartType('bar')} aria-label="Bar chart">📊</button>
        </div>
      </div>
      <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginBottom: '16px' }}>
        {Object.entries(SERIES_CONFIG).map(([k, c]) => (
          <button key={k} style={tab(key === k)} onClick={() => setKey(k)}>{c.label}</button>
        ))}
      </div>

      {!history ? <Skeleton height={230} /> : series.length < 2 ? (
        <p style={{ color: 'var(--text-dim)', fontSize: '13px', padding: '40px 0', textAlign: 'center' }}>Not enough history yet.</p>
      ) : (
        <HistoryChart series={series} chartType={chartType} isAqi={key === 'aqi'} fmt={fmt} axisLabel={axisLabel} chartKey={`${range}-${key}-${chartType}`} />
      )}

      {series.length >= 2 && (() => {
        const minP = series.reduce((a, b) => (b.value < a.value ? b : a));
        const maxP = series.reduce((a, b) => (b.value > a.value ? b : a));
        return (
          <>
            <p style={{ fontSize: '11px', color: 'var(--text-dim)', textAlign: 'center', marginTop: '4px' }}>
              {fullLabel(series[0].date)} — {fullLabel(series[series.length - 1].date)}
              {available < hours && ` · ${Math.round(available / 24)} days available`}
            </p>
            <div style={{ display: 'flex', gap: '24px', marginTop: '16px' }}>
              <div>
                <p style={{ fontSize: '20px', fontWeight: 700, color: '#22c55e' }}>{fmt(minP.value)}{cfg.unit && ` ${cfg.unit}`}</p>
                <p style={{ fontSize: '11px', color: 'var(--text-dim)' }}>Min. {cfg.label} · {fullLabel(minP.date)}</p>
              </div>
              <div>
                <p style={{ fontSize: '20px', fontWeight: 700, color: '#ef4444' }}>{fmt(maxP.value)}{cfg.unit && ` ${cfg.unit}`}</p>
                <p style={{ fontSize: '11px', color: 'var(--text-dim)' }}>Max. {cfg.label} · {fullLabel(maxP.date)}</p>
              </div>
            </div>
          </>
        );
      })()}
    </Card>
  );
}

function HistoryChart({ series, chartType, isAqi, fmt, axisLabel, chartKey }) {
  const [boxRef, W] = useWidth(700);
  const H = 240, padL = 40, padR = 16, padT = 20, padB = 34;
  const values = series.map((p) => p.value);
  const dataMin = Math.min(...values), dataMax = Math.max(...values);
  const axisMax = dataMax * 1.12 || 1;
  const x = (i) => padL + (i / (series.length - 1)) * (W - padL - padR);
  const y = (v) => H - padB - (v / axisMax) * (H - padT - padB);
  const color = (v) => (isAqi ? getAqiColor(v) : colorForRelative((v - dataMin) / (dataMax - dataMin || 1)));
  const linePath = series.map((p, i) => `${i ? 'L' : 'M'} ${x(i)} ${y(p.value)}`).join(' ');
  const areaPath = `${linePath} L ${x(series.length - 1)} ${H - padB} L ${x(0)} ${H - padB} Z`;
  const barW = ((W - padL - padR) / series.length) * 0.6;
  const stride = Math.ceil(series.length / Math.max(4, Math.floor(W / 90)));

  return (
    <div ref={boxRef}>
    <svg key={chartKey} className="chart-fade" width="100%" height={H} viewBox={`0 0 ${W} ${H}`}>
      {[0, 0.5, 1].map((f) => (
        <g key={f}>
          <line x1={padL} x2={W - padR} y1={y(axisMax * f)} y2={y(axisMax * f)} stroke="var(--border)" strokeDasharray="3 4" />
          <text x={padL - 6} y={y(axisMax * f) + 3} fontSize="10" textAnchor="end" fill="var(--text-dim)">{fmt(axisMax * f)}</text>
        </g>
      ))}
      {chartType === 'line' ? (
        <>
          <path d={areaPath} fill={CHART_ACCENT} opacity="0.12" />
          <path d={linePath} fill="none" stroke={CHART_ACCENT} strokeWidth="2.4" strokeLinejoin="round" />
          {series.length <= 40 && series.map((p, i) => <circle key={i} cx={x(i)} cy={y(p.value)} r="3" fill={color(p.value)} />)}
        </>
      ) : (
        series.map((p, i) => (
          <rect key={i} className="bar-rise" style={{ animationDelay: `${i * 12}ms` }}
            x={x(i) - barW / 2} y={y(p.value)} width={barW} height={Math.max(H - padB - y(p.value), 2)} rx="3" fill={color(p.value)}>
            <title>{fmt(p.value)}</title>
          </rect>
        ))
      )}
      {series.map((p, i) => i % stride === 0 && (
        <text key={`l${i}`} x={x(i)} y={H - 12} fontSize="10" fill="var(--text-dim)" textAnchor="middle">{axisLabel(p.date)}</text>
      ))}
    </svg>
    </div>
  );
}

/* ---------- Page ---------- */
export default function Home() {
  const [data, setData] = useState(null);
  const [timeline, setTimeline] = useState(null);
  const [history, setHistory] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState({ wardId: null, data: null });
  const [error, setError] = useState(null);
  const [attempt, setAttempt] = useState(0);

  // Fire all requests at once; each card renders as soon as its data lands.
  // Hosted backends can take a while to wake, so retry a few times on failure.
  useEffect(() => {
    let retryTimer;
    getForecast('delhi')
      .then((d) => {
        if (!d?.wards?.length) throw new Error(d?.error || 'The API returned no ward data');
        setError(null);
        setData(d);
      })
      .catch((err) => {
        setError(err.message === 'Failed to fetch' || err.name === 'TypeError'
          ? 'No response (the server is not running, the URL is wrong, or CORS blocked this site)'
          : err.message);
        if (attempt < 4) retryTimer = setTimeout(() => setAttempt((a) => a + 1), 3000 * 2 ** attempt);
      });
    getTimeline('delhi').then(setTimeline).catch(() => {});
    getHistory('delhi', { hours: 720 }).then(setHistory).catch(() => {});
    return () => clearTimeout(retryTimer);
  }, [attempt]);

  const wards = useMemo(() => data?.wards ?? [], [data]);
  const worst = useMemo(() => [...wards].sort((a, b) => b.current_aqi - a.current_aqi), [wards]);
  const selectedWard = wards.find((w) => w.ward_id === selectedId) ?? worst[0];

  useEffect(() => {
    if (!selectedWard) return;
    const wardId = selectedWard.ward_id;
    getWardDetail('delhi', wardId).then((d) => setDetail({ wardId, data: d })).catch(() => {});
  }, [selectedWard]);

  const wardDetail = detail.wardId === selectedWard?.ward_id ? detail.data : null;
  const latest = history?.series?.[history.series.length - 1];

  if (error && !data) return (
    <div className="api-error">
      <p className="api-error-title">Couldn&apos;t reach the Atmos API</p>
      <p>{error}</p>
      <p>
        Tried <code>{BASE_URL}/api/forecast/delhi</code>
        {attempt < 4 ? ' · retrying automatically…' : ''}
      </p>
      <button className="api-error-retry" onClick={() => setAttempt((a) => a + 1)}>Retry now</button>
    </div>
  );

  const cityAqi = data ? Math.round(data.city_avg_aqi) : null;
  const cityPm25 = latest ? Math.round(latest.pm25) : null;
  const cityPm10 = latest ? Math.round(latest.pm10) : null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h2 style={{ fontSize: '24px', fontWeight: '700', color: 'var(--text-primary)' }}>
            Delhi AQI forecast
          </h2>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '4px' }}>
            Ward-level predictions for the next 72 hours. Press play or drag the timeline to watch them unfold.
          </p>
        </div>
        <DataSourceBadge data={data} />
      </div>

      {data?.data_source === 'offline-sample' && (
        <div className="notice">
          Live data sources are unreachable, so this shows the bundled sample from {formatTime(data.observed_at, { day: 'numeric', month: 'long', year: 'numeric' })}.
          Forecasts are still produced by the model, but they are not current.
        </div>
      )}

      {/* Spatial hero */}
      {data ? (
        <PredictionMap
          wards={wards}
          timeline={timeline}
          selectedWardId={selectedWard?.ward_id}
          onWardClick={(w) => setSelectedId(w.ward_id)}
        />
      ) : <Skeleton height={560} style={{ borderRadius: 20 }} />}

      {/* Now + prediction */}
      <div className="dash-row">
        {data ? (
          <LiveAqiCard aqi={cityAqi} pm25={cityPm25} pm10={cityPm10} observedAt={data.observed_at} animOrder={0} />
        ) : <Skeleton height={340} style={{ flex: 1 }} />}
        <ForecastCard ward={selectedWard} detail={wardDetail} animOrder={1} />
      </div>

      <div className="dash-row">
        {cityPm25 != null ? (
          <CigaretteCard cigarettes={(cityPm25 / 22).toFixed(1)} pm25={cityPm25} animOrder={2} />
        ) : <Skeleton height={340} style={{ flex: 1 }} />}
        <TopPollutantsCard latest={latest} animOrder={3} />
      </div>

      <HistoricalCard history={history} animOrder={4} />

      {/* Ward rankings */}
      <Card title="All wards — now and in 24h" className="stagger-in" style={{ animationDelay: '0.4s' }}>
        {!data ? <Skeleton height={120} /> : (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
            {worst.map((ward) => {
              const c = getAqiColor(ward.current_aqi);
              const active = selectedWard?.ward_id === ward.ward_id;
              return (
                <button
                  key={ward.ward_id}
                  onClick={() => setSelectedId(ward.ward_id)}
                  className="ward-pill"
                  style={{ '--c': c, background: active ? `${c}22` : undefined }}
                  title={`Forecast in 24h: ${Math.round(ward.forecast_aqi_24h)}`}
                >
                  <span className="dot" />
                  <span className="name">{ward.ward_name}</span>
                  <span className="val">{Math.round(ward.current_aqi)}</span>
                  <span className="next" style={{ color: getAqiColor(ward.forecast_aqi_24h) }}>
                    {ward.trend === 'worsening' ? '↑' : '↓'} {Math.round(ward.forecast_aqi_24h)}
                  </span>
                </button>
              );
            })}
          </div>
        )}
      </Card>

    </div>
  );
}
