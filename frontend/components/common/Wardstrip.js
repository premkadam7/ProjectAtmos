'use client';

import MiniFace from './MiniFace';

/* ================================================================
   WARD STRIP — replaces the "Top 5 Worst Wards" <Card> list.
   A horizontally scrollable row of snap cards instead of a boxed
   vertical list — reads more like a magazine "story strip" than
   a data table.

   Usage in app/page.js, replacing the <Card title="Top 5 Worst Wards">
   block:

     import WardStrip from '@/components/common/WardStrip';
     ...
     <WardStrip
       title="Worst Air Today"
       wards={topWorst}
       selectedWard={selectedWard}
       onSelect={setSelectedWard}
       animOrder={4}
     />
================================================================ */

function getAqiColor(aqi) {
  if (aqi <= 50) return '#4ade80';
  if (aqi <= 100) return '#a3e635';
  if (aqi <= 200) return '#facc15';
  if (aqi <= 300) return '#fb923c';
  if (aqi <= 400) return '#f97316';
  return '#ff8f6b';
}

export default function WardStrip({ title, wards, selectedWard, onSelect, animOrder = 0 }) {
  return (
    <div className="stagger-in" style={{ animationDelay: `${animOrder * 0.08}s` }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '10px', marginBottom: '14px' }}>
        <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '22px', fontWeight: 700, color: 'var(--text-primary)' }}>
          {title}
        </h3>
        <span style={{ fontSize: '12px', color: 'var(--text-dim)' }}>scroll for more →</span>
      </div>

      <div className="ward-strip-scroll">
        {wards.map((ward, i) => {
          const color = getAqiColor(ward.current_aqi);
          const active = selectedWard?.ward_id === ward.ward_id;
          return (
            <div
              key={ward.ward_id}
              onClick={() => onSelect(ward)}
              className="ward-strip-card"
              style={{
                borderColor: active ? color : 'var(--card-border)',
                transform: active ? 'translateY(-4px)' : `rotate(${i % 2 === 0 ? '-0.6deg' : '0.6deg'})`,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
                <MiniFace aqi={ward.current_aqi} size={26} />
                <span style={{ fontSize: '11px', color: 'var(--text-dim)' }}>#{i + 1}</span>
              </div>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                {ward.ward_name}
              </p>
              <p style={{ fontSize: '30px', fontWeight: 800, color, lineHeight: 1 }}>
                {ward.current_aqi}
              </p>
              <span style={{ fontSize: '11px', color: 'var(--text-dim)' }}>
                {ward.trend === 'worsening' ? '↑ worsening' : ward.trend === 'improving' ? '↓ improving' : '→ stable'}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}