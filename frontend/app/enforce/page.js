'use client';

import { useEffect, useState } from 'react';
import { getEnforce } from '@/lib/api';

const urgencyColors = {
  HIGH: '#ef4444',
  MEDIUM: '#f97316',
  LOW: '#facc15',
};

const urgencyBg = {
  HIGH: 'rgba(239, 68, 68, 0.1)',
  MEDIUM: 'rgba(249, 115, 22, 0.1)',
  LOW: 'rgba(250, 204, 21, 0.1)',
};

function getAqiColor(aqi) {
  if (aqi <= 50) return '#4ade80';
  if (aqi <= 100) return '#a3e635';
  if (aqi <= 200) return '#facc15';
  if (aqi <= 300) return '#fb923c';
  if (aqi <= 400) return '#f97316';
  return '#ef4444';
}

export default function EnforcePage() {
  const [data, setData] = useState(null);
  const [filter, setFilter] = useState('ALL');
  const [sort, setSort] = useState('urgency');

  useEffect(() => {
    getEnforce('delhi').then(setData);
  }, []);

  if (!data) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh', color: 'var(--text-dim)' }}>
      Loading...
    </div>
  );

  const filtered = data.tickets
    .filter(t => filter === 'ALL' || t.urgency === filter)
    .sort((a, b) => {
      if (sort === 'urgency') {
        const order = { HIGH: 0, MEDIUM: 1, LOW: 2 };
        return order[a.urgency] - order[b.urgency];
      }
      if (sort === 'aqi') return b.current_aqi - a.current_aqi;
      if (sort === 'population') return b.affected_population - a.affected_population;
      return 0;
    });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>

      {/* Header */}
      <div>
        <h2 style={{ fontSize: '24px', fontWeight: '700', color: 'var(--text-primary)' }}>Enforcement</h2>
        <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '4px' }}>
          Prioritised, evidence-backed enforcement recommendations for city authorities
        </p>
      </div>

      {/* Summary bar */}
      <div style={{ display: 'flex', gap: '16px' }}>
        <div className="card" style={{ flex: 1, textAlign: 'center' }}>
          <p style={{ fontSize: '28px', fontWeight: '700', color: 'var(--text-primary)' }}>{data.total_tickets}</p>
          <p style={{ fontSize: '12px', color: 'var(--text-dim)', marginTop: '4px' }}>Total Tickets</p>
        </div>
        <div className="card" style={{ flex: 1, textAlign: 'center' }}>
          <p style={{ fontSize: '28px', fontWeight: '700', color: '#ef4444' }}>{data.high_urgency_count}</p>
          <p style={{ fontSize: '12px', color: 'var(--text-dim)', marginTop: '4px' }}>High Urgency</p>
        </div>
        <div className="card" style={{ flex: 1, textAlign: 'center' }}>
          <p style={{ fontSize: '28px', fontWeight: '700', color: 'var(--accent-primary)' }}>{data.wards_affected}</p>
          <p style={{ fontSize: '12px', color: 'var(--text-dim)', marginTop: '4px' }}>Wards Affected</p>
        </div>
      </div>

      {/* Filters and sort */}
      <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
        <span style={{ fontSize: '12px', color: 'var(--text-dim)' }}>Filter:</span>
        {['ALL', 'HIGH', 'MEDIUM', 'LOW'].map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            style={{
              padding: '6px 14px',
              borderRadius: '20px',
              border: '1px solid',
              borderColor: filter === f ? (urgencyColors[f] || 'var(--accent-primary)') : 'var(--border)',
              background: filter === f ? (urgencyBg[f] || 'rgba(92, 224, 210, 0.1)') : 'transparent',
              color: filter === f ? (urgencyColors[f] || 'var(--accent-primary)') : 'var(--text-secondary)',
              fontSize: '12px',
              fontWeight: '600',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
            }}
          >
            {f}
          </button>
        ))}
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '12px', color: 'var(--text-dim)' }}>Sort by:</span>
          <select
            value={sort}
            onChange={e => setSort(e.target.value)}
            style={{
              padding: '6px 12px',
              borderRadius: '8px',
              border: '1px solid var(--border)',
              background: 'var(--bg-tertiary)',
              color: 'var(--text-primary)',
              fontSize: '12px',
              cursor: 'pointer',
              outline: 'none',
            }}
          >
            <option value="urgency">Urgency</option>
            <option value="aqi">Current AQI</option>
            <option value="population">Population</option>
          </select>
        </div>
      </div>

      {/* Ticket list */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {filtered.map((ticket) => (
          <div
            key={ticket.ticket_id}
            className="card"
            style={{ padding: '0', overflow: 'hidden' }}
          >
            <div style={{ display: 'flex' }}>
              {/* Urgency bar */}
              <div style={{
                width: '4px',
                background: urgencyColors[ticket.urgency],
                flexShrink: 0,
                boxShadow: `0 0 8px ${urgencyColors[ticket.urgency]}80`,
              }} />

              <div style={{ flex: 1, padding: '16px 20px', display: 'flex', gap: '16px', alignItems: 'flex-start' }}>

                {/* Main content */}
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                    <span style={{
                      padding: '2px 8px',
                      borderRadius: '4px',
                      background: urgencyBg[ticket.urgency],
                      color: urgencyColors[ticket.urgency],
                      fontSize: '10px',
                      fontWeight: '700',
                      letterSpacing: '0.05em',
                    }}>
                      {ticket.urgency}
                    </span>
                    <span style={{ fontSize: '11px', color: 'var(--text-dim)' }}>{ticket.ticket_id}</span>
                    <span style={{ fontSize: '13px', fontWeight: '600', color: 'var(--text-primary)' }}>
                      {ticket.ward_name}
                    </span>
                  </div>

                  <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '8px' }}>
                    {ticket.primary_cause_icon} Primary cause: <span style={{ color: 'var(--text-primary)', fontWeight: '600' }}>{ticket.primary_cause}</span> ({ticket.primary_cause_percentage}%)
                  </p>

                  <p style={{ fontSize: '13px', color: 'var(--accent-primary)', fontWeight: '500' }}>
                    → {ticket.recommended_action}
                  </p>

                  <div style={{ display: 'flex', gap: '16px', marginTop: '10px' }}>
                    <span style={{ fontSize: '11px', color: 'var(--text-dim)' }}>
                      👥 {ticket.affected_population.toLocaleString()} people
                    </span>
                    {ticket.schools_in_zone > 0 && (
                      <span style={{ fontSize: '11px', color: 'var(--text-dim)' }}>
                        🏫 {ticket.schools_in_zone} school{ticket.schools_in_zone > 1 ? 's' : ''}
                      </span>
                    )}
                    {ticket.hospitals_in_zone > 0 && (
                      <span style={{ fontSize: '11px', color: 'var(--text-dim)' }}>
                        🏥 {ticket.hospitals_in_zone} hospital{ticket.hospitals_in_zone > 1 ? 's' : ''}
                      </span>
                    )}
                  </div>
                </div>

                {/* Right side stats */}
                <div style={{ textAlign: 'right', flexShrink: 0 }}>
                  <p style={{ fontSize: '24px', fontWeight: '700', color: getAqiColor(ticket.current_aqi) }}>
                    {ticket.current_aqi}
                  </p>
                  <p style={{ fontSize: '11px', color: 'var(--text-dim)' }}>Current AQI</p>
                  
                  <div style={{ marginTop: '12px', background: 'var(--bg-tertiary)', padding: '6px 10px', borderRadius: '6px', border: '1px solid var(--border)', cursor: 'help' }} title={`ML Counterfactual Simulation: ${ticket.recommended_action} for 48h`}>
                    <p style={{ fontSize: '10px', color: 'var(--text-dim)', marginBottom: '2px', textAlign: 'right' }}>ML Simulation</p>
                    <p style={{ fontSize: '14px', color: '#4ade80', fontWeight: '700', textAlign: 'right' }}>
                      ↓ {ticket.estimated_aqi_reduction}
                    </p>
                  </div>
                </div>

              </div>
            </div>
          </div>
        ))}

        {filtered.length === 0 && (
          <div className="card" style={{ textAlign: 'center', padding: '40px', color: 'var(--text-dim)' }}>
            No tickets match the selected filter.
          </div>
        )}
      </div>

    </div>
  );
}