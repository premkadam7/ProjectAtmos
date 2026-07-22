'use client';

import { useState, useEffect } from 'react';
import { getForecast, getBlame } from '@/lib/api';

const blameColors = {
  'Traffic & Time': '#3b82f6',
  'Historical / Baseline': '#8b5cf6',
  'Geography & Infra': '#a3a3a3',
  'Weather': '#06b6d4',
};

function getAqiColor(aqi) {
  if (aqi <= 50) return '#4ade80';
  if (aqi <= 100) return '#a3e635';
  if (aqi <= 200) return '#facc15';
  if (aqi <= 300) return '#fb923c';
  if (aqi <= 400) return '#f97316';
  return '#ef4444';
}

export default function BlamePage() {
  const [allWards, setAllWards] = useState([]);
  const [selected, setSelected] = useState(null);
  const [search, setSearch] = useState('');
  const [blameData, setBlameData] = useState(null);

  useEffect(() => {
    getForecast('delhi').then((data) => {
      const wards = Array.isArray(data) ? data : (data?.wards || []);
      const sorted = [...wards].sort((a, b) => b.current_aqi - a.current_aqi);
      setAllWards(sorted);
      if (sorted.length > 0) {
        setSelected(sorted[0]);
      }
    });
  }, []);

  useEffect(() => {
    if (selected) {
      setBlameData(null);
      getBlame('delhi', selected.ward_id).then(setBlameData);
    }
  }, [selected]);

  const searchResults = search.length > 0
    ? allWards.filter(w => w.ward_name.toLowerCase().includes(search.toLowerCase()))
    : [];

  const displayList = search.length > 0 ? searchResults : allWards.slice(0, 5);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>

      <div>
        <h2 style={{ fontSize: '24px', fontWeight: '700', color: 'var(--text-primary)' }}>Blame Score</h2>
        <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '4px' }}>
          Statistical feature attribution — model drivers, not absolute causality
        </p>
      </div>

      <div style={{ display: 'flex', gap: '16px' }}>

        {/* Ward selector */}
        <div className="card" style={{ width: '280px', flexShrink: 0 }}>

          {/* Search */}
          <input
            type="text"
            placeholder="Search any ward..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{
              width: '100%',
              padding: '8px 12px',
              borderRadius: '8px',
              border: '1px solid var(--glass-border)',
              background: 'var(--bg-tertiary)',
              color: 'var(--text-primary)',
              fontSize: '13px',
              marginBottom: '12px',
              outline: 'none',
            }}
          />

          <p style={{ fontSize: '12px', color: 'var(--text-dim)', marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            {search.length > 0 ? `${searchResults.length} results` : 'Top 5 Worst Wards'}
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {displayList.length === 0 && (
              <p style={{ fontSize: '13px', color: 'var(--text-dim)', padding: '8px' }}>No wards found</p>
            )}
            {displayList.map((ward) => (
              <div
                key={ward.ward_id}
                onClick={() => setSelected(ward)}
                style={{
                  padding: '12px',
                  borderRadius: '10px',
                  cursor: 'pointer',
                  background: selected?.ward_id === ward.ward_id ? 'rgba(92, 224, 210, 0.1)' : 'var(--bg-tertiary)',
                  border: selected?.ward_id === ward.ward_id ? '1px solid rgba(92, 224, 210, 0.3)' : '1px solid transparent',
                  transition: 'all 0.2s ease',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '13px', color: 'var(--text-primary)', fontWeight: selected?.ward_id === ward.ward_id ? '600' : '400' }}>
                    {ward.ward_name}
                  </span>
                  <span style={{ fontSize: '13px', fontWeight: '700', color: getAqiColor(ward.current_aqi) }}>
                    {ward.current_aqi}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Blame breakdown */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '16px' }}>

          {selected && blameData && !blameData.error ? (
            <>
              <div className="card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <h3 style={{ fontSize: '20px', fontWeight: '700', color: 'var(--text-primary)' }}>{selected.ward_name}</h3>
                    <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                      AQI <span style={{ color: getAqiColor(selected.current_aqi), fontWeight: '700' }}>{selected.current_aqi}</span> — primary driver: {blameData.factors[0].icon} <span style={{ color: 'var(--accent-primary)', textTransform: 'capitalize' }}>{blameData.factors[0].name}</span>
                    </p>
                  </div>
                  <div style={{
                    padding: '8px 16px',
                    borderRadius: '20px',
                    background: 'rgba(92, 224, 210, 0.1)',
                    border: '1px solid rgba(92, 224, 210, 0.2)',
                    fontSize: '11px',
                    color: 'var(--accent-primary)',
                  }}>
                    Statistical Attribution
                  </div>
                </div>
              </div>

              <div className="card">
                <p style={{ fontSize: '14px', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '20px' }}>Source Attribution Breakdown</p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  {blameData.factors.map((f) => (
                      <div key={f.name}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                          <span style={{ fontSize: '13px', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <span>{f.icon}</span>
                            <span style={{ textTransform: 'capitalize' }}>{f.name}</span>
                          </span>
                          <span style={{ fontSize: '13px', fontWeight: '700', color: blameColors[f.name] || '#ffffff' }}>{f.percentage}%</span>
                        </div>
                        <div style={{ height: '8px', background: 'var(--bg-tertiary)', borderRadius: '4px', overflow: 'hidden' }}>
                          <div style={{
                            width: `${f.percentage}%`,
                            height: '100%',
                            background: blameColors[f.name] || '#ffffff',
                            borderRadius: '4px',
                            transition: 'width 0.5s ease',
                            boxShadow: `0 0 8px ${blameColors[f.name] || '#ffffff'}60`,
                          }} />
                        </div>
                      </div>
                    ))}
                </div>
              </div>

              <div className="card">
                <p style={{ fontSize: '14px', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '16px' }}>Attribution Distribution</p>
                <div style={{ display: 'flex', alignItems: 'center', gap: '32px' }}>
                  <div style={{ position: 'relative', width: '120px', height: '120px', flexShrink: 0 }}>
                    <svg viewBox="0 0 36 36" style={{ transform: 'rotate(-90deg)', width: '120px', height: '120px' }}>
                      {(() => {
                        let offset = 0;
                        return blameData.factors.map((f) => {
                            const el = (
                              <circle
                                key={f.name}
                                cx="18" cy="18" r="15.9"
                                fill="transparent"
                                stroke={blameColors[f.name] || '#ffffff'}
                                strokeWidth="3.2"
                                strokeDasharray={`${f.percentage} ${100 - f.percentage}`}
                                strokeDashoffset={-offset}
                              />
                            );
                            offset += f.percentage;
                            return el;
                          });
                      })()}
                    </svg>
                    <div style={{
                      position: 'absolute',
                      top: '50%',
                      left: '50%',
                      transform: 'translate(-50%, -50%)',
                      textAlign: 'center',
                    }}>
                      <div style={{ fontSize: '11px', color: 'var(--text-dim)' }}>top</div>
                      <div style={{ fontSize: '12px', fontWeight: '700', color: blameColors[blameData.factors[0].name] || '#ffffff', textTransform: 'capitalize' }}>
                        {blameData.factors[0].name.split(' ')[0]}
                      </div>
                    </div>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', flex: 1 }}>
                    {blameData.factors.map((f) => (
                        <div key={f.name} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <div style={{ width: '10px', height: '10px', borderRadius: '2px', background: blameColors[f.name] || '#ffffff', flexShrink: 0 }} />
                          <span style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'capitalize', flex: 1 }}>{f.name}</span>
                          <span style={{ fontSize: '12px', fontWeight: '600', color: blameColors[f.name] || '#ffffff' }}>{f.percentage}%</span>
                        </div>
                      ))}
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-dim)' }}>
              Loading data...
            </div>
          )}

        </div>
      </div>
    </div>
  );
}