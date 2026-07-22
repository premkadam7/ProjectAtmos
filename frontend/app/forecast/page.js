'use client';

import { useEffect, useState } from 'react';
import { getForecast, getWardDetail, getBlame } from '@/lib/api';
import Card from '@/components/common/Card';
import dynamic from 'next/dynamic';

const AqiMap = dynamic(() => import('@/components/common/AqiMap'), {
  ssr: false,
  loading: () => (
    <div style={{ height: '500px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-dim)' }}>
      Loading map…
    </div>
  ),
});

const CHART_ACCENT = '#5cb9ad';

function getAqiColor(aqi) {
  if (aqi == null) return '#6b7280';
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

function getTrendIcon(trend) {
  if (trend === 'worsening') return '↑';
  if (trend === 'improving') return '↓';
  return '→';
}

function getTrendColor(trend) {
  if (trend === 'worsening') return '#ef4444';
  if (trend === 'improving') return '#4ade80';
  return '#facc15';
}

const BLAME_COLORS = {
  'Traffic & Time':        '#3b82f6',
  'Weather':               '#06b6d4',
  'Historical / Baseline': '#8b5cf6',
  'Geography & Infra':     '#f97316',
  'Other':                 '#a3a3a3',
};

/* ---------- Ward Detail Panel ---------- */
function WardDetailPanel({ ward, detail, blame, onClose }) {
  if (!ward) return null;

  const color = getAqiColor(ward.current_aqi);
  const cigarettes = ward.cigarette_equivalent?.toFixed(1) || (ward.current_aqi * 0.42 / 22).toFixed(1);

  const W = 420, H = 140, padL = 28, padR = 12, padT = 16, padB = 24;
  const hourly = detail?.hourly || [];
  const allVals = hourly.flatMap(h => [h.aqi_low, h.aqi_high]);
  const max = allVals.length ? Math.max(...allVals) + 20 : ward.current_aqi + 50;
  const min = allVals.length ? Math.max(0, Math.min(...allVals) - 20) : Math.max(0, ward.current_aqi - 50);

  const x = (i) => padL + (i / Math.max(hourly.length - 1, 1)) * (W - padL - padR);
  const y = (v) => H - padB - ((v - min) / (max - min || 1)) * (H - padT - padB);

  const linePath = hourly.map((h, i) => `${i === 0 ? 'M' : 'L'} ${x(i)} ${y(h.aqi)}`).join(' ');
  const topPath = hourly.map((h, i) => `${i === 0 ? 'M' : 'L'} ${x(i)} ${y(h.aqi_high)}`).join(' ');
  const bottomPath = hourly.slice().reverse().map((h, i) => `L ${x(hourly.length - 1 - i)} ${y(h.aqi_low)}`).join(' ');
  const bandPath = hourly.length ? `${topPath} ${bottomPath} Z` : '';

  return (
    <div style={{
      position: 'fixed',
      right: 0, top: 0, bottom: 0,
      width: '380px',
      background: 'var(--card-bg)',
      backdropFilter: 'blur(20px)',
      WebkitBackdropFilter: 'blur(20px)',
      borderLeft: '1px solid var(--card-border)',
      zIndex: 500,
      display: 'flex',
      flexDirection: 'column',
      boxShadow: '-8px 0 32px rgba(0,0,0,0.15)',
      animation: 'slideInRight 0.3s ease forwards',
      overflowY: 'auto',
    }}>

      {/* Header */}
      <div style={{ padding: '20px 20px 16px', borderBottom: '1px solid var(--card-border)', flexShrink: 0 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h3 style={{ fontSize: '18px', fontWeight: '700', color: 'var(--text-primary)' }}>{ward.ward_name}</h3>
            <p style={{ fontSize: '12px', color: 'var(--text-dim)', marginTop: '2px' }}>Delhi, India</p>
          </div>
          <button
            onClick={onClose}
            style={{ background: 'transparent', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '18px', lineHeight: 1, padding: '4px' }}
          >
            ✕
          </button>
        </div>

        {/* AQI + trend */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginTop: '16px' }}>
          <div>
            <span style={{ fontSize: '52px', fontWeight: '800', color, lineHeight: 1, letterSpacing: '-1px' }}>
              {ward.current_aqi}
            </span>
            <p style={{ fontSize: '13px', color, fontWeight: '600', marginTop: '2px' }}>{getAqiLabel(ward.current_aqi)}</p>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <div style={{ padding: '4px 10px', borderRadius: '20px', background: `${getTrendColor(ward.trend)}15`, border: `1px solid ${getTrendColor(ward.trend)}30` }}>
              <span style={{ fontSize: '12px', fontWeight: '600', color: getTrendColor(ward.trend) }}>
                {getTrendIcon(ward.trend)} {ward.trend || 'stable'}
              </span>
            </div>
            <p style={{ fontSize: '11px', color: 'var(--text-dim)' }}>🚬 {cigarettes} cigs/day</p>
          </div>
        </div>

        {/* 24/48/72h forecast pills */}
        <div style={{ display: 'flex', gap: '8px', marginTop: '14px' }}>
          {[
            { label: '+24h', val: ward.forecast_aqi_24h },
            { label: '+48h', val: ward.forecast_aqi_48h },
            { label: '+72h', val: ward.forecast_aqi_72h },
          ].map(f => (
            <div key={f.label} style={{
              flex: 1, textAlign: 'center', padding: '8px 6px',
              background: `${getAqiColor(f.val)}12`,
              border: `1px solid ${getAqiColor(f.val)}30`,
              borderRadius: '10px',
            }}>
              <p style={{ fontSize: '10px', color: 'var(--text-dim)', marginBottom: '3px' }}>{f.label}</p>
              <p style={{ fontSize: '18px', fontWeight: '700', color: getAqiColor(f.val) }}>{f.val}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Hourly forecast chart */}
      {hourly.length > 0 && (
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--card-border)' }}>
          <p style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '10px' }}>Hourly Forecast</p>
          <svg width="100%" height={H} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="xMidYMid meet">
            <path d={bandPath} fill={CHART_ACCENT} opacity="0.12" stroke="none" />
            <path d={linePath} fill="none" stroke={CHART_ACCENT} strokeWidth="2" />
            {[0, Math.floor(hourly.length / 2), hourly.length - 1].map(i => (
              hourly[i] && (
                <g key={i}>
                  <circle cx={x(i)} cy={y(hourly[i].aqi)} r="3.5" fill={CHART_ACCENT} />
                  <text x={x(i)} y={H - 8} fontSize="9" fill="var(--text-dim)" textAnchor="middle">
                    {new Date(hourly[i].timestamp).toLocaleTimeString('en-IN', { hour: 'numeric', hour12: true })}
                  </text>
                </g>
              )
            ))}
          </svg>
          <div style={{ display: 'flex', gap: '12px', marginTop: '4px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
              <div style={{ width: '12px', height: '2px', background: CHART_ACCENT }} />
              <span style={{ fontSize: '10px', color: 'var(--text-dim)' }}>Forecast</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
              <div style={{ width: '12px', height: '8px', background: CHART_ACCENT, opacity: 0.12, borderRadius: '2px' }} />
              <span style={{ fontSize: '10px', color: 'var(--text-dim)' }}>Uncertainty</span>
            </div>
          </div>
        </div>
      )}

      {/* Blame score */}
      {blame && (
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--card-border)' }}>
          <p style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '10px' }}>
            Pollution Attribution
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {blame.factors.map(f => (
              <div key={f.name}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>{f.icon} {f.name}</span>
                  <span style={{ fontSize: '12px', fontWeight: '700', color: BLAME_COLORS[f.name] || CHART_ACCENT }}>{f.percentage}%</span>
                </div>
                <div style={{ height: '5px', background: 'var(--bg-tertiary)', borderRadius: '3px', overflow: 'hidden' }}>
                  <div style={{
                    width: `${f.percentage}%`, height: '100%',
                    background: BLAME_COLORS[f.name] || CHART_ACCENT,
                    borderRadius: '3px', transition: 'width 0.5s ease',
                  }} />
                </div>
              </div>
            ))}
          </div>
          {blame.explanation && (
            <p style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '12px', lineHeight: 1.5, fontStyle: 'italic' }}>
              {blame.explanation}
            </p>
          )}
          <p style={{ fontSize: '10px', color: 'var(--text-dim)', marginTop: '8px', opacity: 0.7 }}>
            Statistical feature attribution — not absolute causality
          </p>
        </div>
      )}

      {/* PM readings */}
      {detail && (
        <div style={{ padding: '16px 20px' }}>
          <p style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '10px' }}>Current Readings</p>
          <div style={{ display: 'flex', gap: '12px' }}>
            <div style={{ flex: 1, padding: '10px', background: 'var(--bg-tertiary)', borderRadius: '8px', textAlign: 'center' }}>
              <p style={{ fontSize: '10px', color: 'var(--text-dim)' }}>PM2.5</p>
              <p style={{ fontSize: '18px', fontWeight: '700', color: 'var(--text-primary)' }}>{detail.current_pm25}</p>
              <p style={{ fontSize: '10px', color: 'var(--text-dim)' }}>µg/m³</p>
            </div>
            <div style={{ flex: 1, padding: '10px', background: 'var(--bg-tertiary)', borderRadius: '8px', textAlign: 'center' }}>
              <p style={{ fontSize: '10px', color: 'var(--text-dim)' }}>Cigarettes</p>
              <p style={{ fontSize: '18px', fontWeight: '700', color: '#ff8f3e' }}>{detail.cigarette_equivalent?.toFixed(1)}</p>
              <p style={{ fontSize: '10px', color: 'var(--text-dim)' }}>per day</p>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}

/* ========== PAGE ========== */
export default function ForecastPage() {
  const [forecastData, setForecastData] = useState(null);
  const [selectedWard, setSelectedWard] = useState(null);
  const [wardDetail, setWardDetail]     = useState(null);
  const [blame, setBlame]               = useState(null);
  const [search, setSearch]             = useState('');

  useEffect(() => {
    getForecast('delhi').then(setForecastData);
  }, []);

  useEffect(() => {
    if (!selectedWard) return;
    setWardDetail(null);
    setBlame(null);
    getWardDetail('delhi', selectedWard.ward_id).then(setWardDetail);
    getBlame('delhi', selectedWard.ward_id).then(setBlame);
  }, [selectedWard]);

  const wards = forecastData?.wards || [];

  const filteredWards = search.length > 1
    ? wards.filter(w => w.ward_name.toLowerCase().includes(search.toLowerCase()))
    : [];

  function handleWardClick(ward) {
    setSelectedWard(ward);
    setSearch('');
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

      {/* Header + search */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '16px' }}>
        <div>
          <h2 style={{ fontSize: '24px', fontWeight: '700', color: 'var(--text-primary)' }}>Forecast Map</h2>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '4px' }}>
            Hyperlocal 24-72hr AQI forecast — click any ward for details
          </p>
        </div>

        {/* Ward search */}
        <div style={{ position: 'relative', width: '280px', flexShrink: 0 }}>
          <input
            type="text"
            placeholder="Search ward..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{
              width: '100%', padding: '9px 14px 9px 36px',
              borderRadius: '20px', border: '1px solid var(--card-border)',
              background: 'var(--card-bg)', color: 'var(--text-primary)',
              fontSize: '13px', outline: 'none',
              transition: 'border-color 0.2s ease',
            }}
          />
          <span style={{ position: 'absolute', left: '12px', top: '10px', color: 'var(--text-dim)', fontSize: '14px' }}>🔍</span>

          {/* Search dropdown */}
          {filteredWards.length > 0 && (
            <div style={{
              position: 'absolute', top: '44px', left: 0, right: 0, zIndex: 200,
              background: 'var(--card-bg)', border: '1px solid var(--card-border)',
              borderRadius: '12px', overflow: 'hidden',
              boxShadow: '0 8px 24px rgba(0,0,0,0.12)',
            }}>
              {filteredWards.slice(0, 6).map(w => (
                <div
                  key={w.ward_id}
                  onClick={() => handleWardClick(w)}
                  style={{
                    padding: '10px 14px', cursor: 'pointer',
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    borderBottom: '1px solid var(--card-border)',
                    transition: 'background 0.15s ease',
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-tertiary)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                >
                  <span style={{ fontSize: '13px', color: 'var(--text-primary)' }}>{w.ward_name}</span>
                  <span style={{ fontSize: '13px', fontWeight: '700', color: getAqiColor(w.current_aqi) }}>{w.current_aqi}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Map */}
      <Card style={{ padding: 0, overflow: 'visible' }}>
        {forecastData ? (
          <AqiMap wards={wards} onWardClick={handleWardClick} />
        ) : (
          <div style={{ height: '500px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-dim)' }}>
            Loading map…
          </div>
        )}
      </Card>

      {/* Ward summary table */}
      <Card title="All Wards — AQI Summary">
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {[...wards].sort((a, b) => b.current_aqi - a.current_aqi).map((ward, i) => (
            <div
              key={ward.ward_id}
              onClick={() => handleWardClick(ward)}
              style={{
                display: 'flex', alignItems: 'center', gap: '12px',
                padding: '6px 8px', borderRadius: '8px', cursor: 'pointer',
                background: selectedWard?.ward_id === ward.ward_id ? 'rgba(92,224,210,0.08)' : 'transparent',
                transition: 'background 0.2s ease',
              }}
              onMouseEnter={e => { if (selectedWard?.ward_id !== ward.ward_id) e.currentTarget.style.background = 'var(--bg-tertiary)'; }}
              onMouseLeave={e => { if (selectedWard?.ward_id !== ward.ward_id) e.currentTarget.style.background = 'transparent'; }}
            >
              <span style={{ fontSize: '11px', color: 'var(--text-dim)', width: '20px', flexShrink: 0 }}>{i + 1}</span>
              <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: getAqiColor(ward.current_aqi), flexShrink: 0 }} />
              <span style={{ flex: 1, fontSize: '13px', color: 'var(--text-primary)' }}>{ward.ward_name}</span>
              <div style={{ flex: 2, height: '5px', background: 'var(--bg-tertiary)', borderRadius: '3px', overflow: 'hidden' }}>
                <div style={{ width: `${(ward.current_aqi / 500) * 100}%`, height: '100%', background: getAqiColor(ward.current_aqi), borderRadius: '3px' }} />
              </div>
              <span style={{ fontSize: '12px', color: 'var(--text-secondary)', width: '70px', textAlign: 'center' }}>
                {getAqiLabel(ward.current_aqi)}
              </span>
              <span style={{ fontSize: '13px', fontWeight: '700', color: getAqiColor(ward.current_aqi), width: '36px', textAlign: 'right' }}>
                {ward.current_aqi}
              </span>
              <span style={{ fontSize: '12px', color: getTrendColor(ward.trend), width: '16px', textAlign: 'center' }}>
                {getTrendIcon(ward.trend)}
              </span>
            </div>
          ))}
          {wards.length === 0 && (
            <p style={{ fontSize: '13px', color: 'var(--text-dim)', padding: '16px', textAlign: 'center' }}>Loading ward data…</p>
          )}
        </div>
      </Card>

      {/* Ward detail slide-in panel */}
      {selectedWard && (
        <WardDetailPanel
          ward={selectedWard}
          detail={wardDetail}
          blame={blame}
          onClose={() => setSelectedWard(null)}
        />
      )}

    </div>
  );
}