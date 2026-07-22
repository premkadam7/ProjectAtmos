'use client';

import { useEffect, useState, useRef } from 'react';
import { MapContainer, TileLayer, GeoJSON, CircleMarker, Tooltip } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

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

function getCentroid(geometry) {
  const coords = geometry.type === 'Polygon' ? geometry.coordinates[0] : geometry.coordinates[0][0];
  let x = 0, y = 0;
  coords.forEach(([lon, lat]) => { x += lon; y += lat; });
  return { lon: x / coords.length, lat: y / coords.length };
}

function distance(a, b) {
  return Math.hypot(a.lat - b.lat, a.lon - b.lon);
}

function seededAqi(name) {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = (hash * 31 + name.charCodeAt(i)) >>> 0;
  }
  return 90 + (hash % 260);
}

const LEGEND_STOPS = [
  { range: '0 - 50',   label: 'Good',        color: '#4ade80' },
  { range: '51 - 100', label: 'Satisfactory', color: '#a3e635' },
  { range: '101 - 200',label: 'Moderate',     color: '#facc15' },
  { range: '201 - 300',label: 'Poor',         color: '#fb923c' },
  { range: '301 - 400',label: 'Very Poor',    color: '#f97316' },
  { range: '401 - 500',label: 'Severe',       color: '#ef4444' },
];

const VULN_CONFIG = {
  hospital:    { color: '#ef4444', emoji: '🏥', label: 'Hospitals' },
  school:      { color: '#3b82f6', emoji: '🏫', label: 'Schools' },
  elderly_care:{ color: '#a78bfa', emoji: '👴', label: 'Elderly Care' },
};

export default function AqiMap({ wards = [], onWardClick }) {
  const [geoData, setGeoData]       = useState(null);
  const [wardAqiMap, setWardAqiMap] = useState(null);
  const [vulnData, setVulnData]     = useState([]);
  const [hoveredWard, setHoveredWard] = useState(null);
  const [showVuln, setShowVuln]     = useState({ hospital: true, school: true, elderly_care: false });
  const geoJsonRef = useRef(null);

  /* Load ward GeoJSON + assign AQI */
  useEffect(() => {
    fetch('/data/delhi_wards.geojson')
      .then(r => r.json())
      .then(data => {
        setGeoData(data);

        const nameToCentroid = data.features.map(f => ({
          name: f.properties?.Ward_Name,
          centroid: getCentroid(f.geometry),
        }));

        const assigned = new Map();
        wards.forEach(mockWard => {
          if (mockWard.lat == null || mockWard.lon == null) return;
          let nearest = null, minDist = Infinity;
          nameToCentroid.forEach(entry => {
            const d = distance({ lat: mockWard.lat, lon: mockWard.lon }, entry.centroid);
            if (d < minDist) { minDist = d; nearest = entry.name; }
          });
          if (nearest) assigned.set(nearest, mockWard);
        });

        const assignedCentroids = [];
        assigned.forEach((mockWard, name) => {
          const entry = nameToCentroid.find(e => e.name === name);
          if (entry) {
            assignedCentroids.push({ name, centroid: entry.centroid, mockWard });
          }
        });

        const result = new Map();
        data.features.forEach(f => {
          const name = f.properties?.Ward_Name;
          if (!name) return;
          const realMatch = assigned.get(name);
          if (realMatch) {
            result.set(name, { aqi: realMatch.current_aqi, isReal: true, sourceWard: realMatch });
          } else {
            const myCentroid = getCentroid(f.geometry);
            let nearestMock = null;
            let minDist = Infinity;
            assignedCentroids.forEach(ac => {
              const d = distance(myCentroid, ac.centroid);
              if (d < minDist) {
                minDist = d;
                nearestMock = ac.mockWard;
              }
            });
            const interpolatedAqi = nearestMock ? nearestMock.current_aqi : seededAqi(name);
            result.set(name, { aqi: interpolatedAqi, isReal: false });
          }
        });
        setWardAqiMap(result);
      })
      .catch(err => console.error('Failed to load ward geometry:', err));
  }, [wards]);

  /* Load vulnerable locations */
  useEffect(() => {
    fetch('/data/vulnerable_locations.geojson')
      .then(r => r.json())
      .then(data => {
        const points = data.features.map(f => ({
          lat: f.geometry.coordinates[1],
          lon: f.geometry.coordinates[0],
          name: f.properties.name,
          type: f.properties.type,
          ward_name: f.properties.ward_name,
        }));
        setVulnData(points);
      })
      .catch(() => {}); // silently fail if file missing
  }, []);

  function styleFeature(feature) {
    const name = feature.properties?.Ward_Name;
    const entry = wardAqiMap?.get(name);
    const aqi = entry?.aqi ?? null;
    return {
      fillColor: getAqiColor(aqi),
      fillOpacity: entry?.isReal ? 0.75 : 0.45,
      color: getAqiColor(aqi),
      weight: entry?.isReal ? 2 : 0.75,
      opacity: 0.9,
    };
  }

  function onEachFeature(feature, layer) {
    const name = feature.properties?.Ward_Name;
    const entry = wardAqiMap?.get(name);
    layer.on({
      mouseover: e => {
        e.target.setStyle({ weight: 2.5, fillOpacity: (entry?.isReal ? 0.75 : 0.45) + 0.15 });
        setHoveredWard({ name: entry?.sourceWard?.ward_name || name, ...entry });
      },
      mouseout: e => {
        e.target.setStyle(styleFeature(feature));
        setHoveredWard(null);
      },
      click: () => entry?.sourceWard && onWardClick && onWardClick(entry.sourceWard),
    });
  }

  if (!geoData || !wardAqiMap) {
    return (
      <div style={{ height: '500px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-dim)' }}>
        Loading map…
      </div>
    );
  }

  const visibleVuln = vulnData.filter(v => showVuln[v.type]);

  return (
    <div style={{ display: 'flex', gap: '16px' }}>

      {/* Map */}
      <div style={{ flex: 1, height: '500px', borderRadius: '12px', overflow: 'hidden', position: 'relative' }}>
        <MapContainer
          center={[28.6139, 77.209]}
          zoom={10}
          style={{ height: '100%', width: '100%', background: 'var(--bg-tertiary)' }}
          scrollWheelZoom={true}
        >
          <TileLayer
            url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
            attribution='&copy; OpenStreetMap contributors &copy; CARTO'
          />
          <GeoJSON
            key={wardAqiMap.size}
            ref={geoJsonRef}
            data={geoData}
            style={styleFeature}
            onEachFeature={onEachFeature}
          />
          {/* Vulnerable location markers */}
          {visibleVuln.map((v, i) => (
            <CircleMarker
              key={i}
              center={[v.lat, v.lon]}
              radius={6}
              fillColor={VULN_CONFIG[v.type]?.color || '#fff'}
              color="white"
              weight={1.5}
              fillOpacity={0.9}
            >
              <Tooltip sticky>
                <span style={{ fontSize: '12px' }}>
                  <strong>{v.name}</strong><br />
                  {VULN_CONFIG[v.type]?.emoji} {v.type.replace('_', ' ')}<br />
                  {v.ward_name}
                </span>
              </Tooltip>
            </CircleMarker>
          ))}
        </MapContainer>

        {/* Hover panel */}
        {hoveredWard && (
          <div style={{
            position: 'absolute', top: '14px', right: '14px', zIndex: 1000,
            width: '190px',
            background: 'var(--glass-bg)',
            backdropFilter: 'blur(12px)',
            WebkitBackdropFilter: 'blur(12px)',
            border: `1px solid ${getAqiColor(hoveredWard.aqi)}50`,
            borderRadius: '12px', padding: '14px',
            boxShadow: '0 8px 24px -8px rgba(0,0,0,0.4)',
            pointerEvents: 'none',
          }}>
            <p style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '6px' }}>
              {hoveredWard.name}
            </p>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px' }}>
              <span style={{ fontSize: '26px', fontWeight: 700, color: getAqiColor(hoveredWard.aqi) }}>
                {hoveredWard.aqi}
              </span>
              <span style={{ fontSize: '11px', color: 'var(--text-dim)' }}>AQI</span>
            </div>
            <p style={{ fontSize: '12px', color: getAqiColor(hoveredWard.aqi), marginTop: '2px' }}>
              {getAqiLabel(hoveredWard.aqi)}
            </p>
            {!hoveredWard.isReal && (
              <p style={{ fontSize: '10px', color: 'var(--text-dim)', marginTop: '6px', fontStyle: 'italic' }}>
                Estimated value
              </p>
            )}
          </div>
        )}
      </div>

      {/* Right panel: legend + vulnerability toggles */}
      <div style={{ width: '170px', flexShrink: 0, display: 'flex', flexDirection: 'column', gap: '20px' }}>

        {/* AQI Legend */}
        <div>
          <p style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '10px' }}>AQI Legend</p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {LEGEND_STOPS.map(stop => (
              <div key={stop.label} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: stop.color, flexShrink: 0 }} />
                <span style={{ fontSize: '10px', color: 'var(--text-dim)', width: '44px' }}>{stop.range}</span>
                <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>{stop.label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Vulnerability Overlay Toggles */}
        <div>
          <p style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '10px' }}>
            Vulnerability Overlay
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {Object.entries(VULN_CONFIG).map(([type, cfg]) => (
              <button
                key={type}
                onClick={() => setShowVuln(prev => ({ ...prev, [type]: !prev[type] }))}
                style={{
                  display: 'flex', alignItems: 'center', gap: '8px',
                  padding: '7px 10px', borderRadius: '8px', cursor: 'pointer',
                  border: `1px solid ${showVuln[type] ? cfg.color + '60' : 'var(--border)'}`,
                  background: showVuln[type] ? `${cfg.color}12` : 'transparent',
                  transition: 'all 0.2s ease',
                  width: '100%',
                }}
              >
                <div style={{
                  width: '8px', height: '8px', borderRadius: '50%',
                  background: showVuln[type] ? cfg.color : 'var(--text-dim)',
                  flexShrink: 0,
                }} />
                <span style={{ fontSize: '11px', color: showVuln[type] ? 'var(--text-primary)' : 'var(--text-dim)', flex: 1, textAlign: 'left' }}>
                  {cfg.emoji} {cfg.label}
                </span>
              </button>
            ))}
          </div>
          <p style={{ fontSize: '10px', color: 'var(--text-dim)', marginTop: '10px', lineHeight: 1.4 }}>
            Colored dots show vulnerable locations. Hover for details.
          </p>
        </div>

      </div>
    </div>
  );
}