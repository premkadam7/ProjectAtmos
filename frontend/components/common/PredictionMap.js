'use client';

import { useEffect, useMemo, useRef, useState, useSyncExternalStore } from 'react';
import { MapContainer, TileLayer, GeoJSON, Marker, ZoomControl, CircleMarker, Tooltip, Pane, useMap, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import { wardEstimate, aqiToPm25 } from '@/lib/spatial';
import 'leaflet/dist/leaflet.css';
import {
  aqiRampColor, getAqiColor, getAqiLabel, loadWardGeometry, formatHourLabel,
} from '@/lib/aqi';
import { getVulnerable } from '@/lib/api';

const DELHI_CENTER = [28.6139, 77.209];
const PLAY_INTERVAL_MS = 350;

const VULN_CONFIG = {
  hospital:     { color: '#ef4444', label: 'Hospitals' },
  school:       { color: '#3b82f6', label: 'Schools' },
  elderly_care: { color: '#a78bfa', label: 'Elderly care' },
};

// Track the app theme (ThemeToggle toggles the `light` class on <html>)
function subscribeTheme(cb) {
  const obs = new MutationObserver(cb);
  obs.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
  return () => obs.disconnect();
}
const isLightTheme = () => document.documentElement.classList.contains('light');

// Frame the whole city, leaving room for the overlay panels
function FitToCity({ geo }) {
  const map = useMap();
  useEffect(() => {
    if (!geo) return;
    const narrow = map.getSize().x < 760;
    map.fitBounds(L.geoJSON(geo).getBounds(), {
      paddingTopLeft: narrow ? [10, 90] : [250, 30],
      paddingBottomRight: narrow ? [10, 100] : [30, 100],
    });
  }, [geo, map]);
  return null;
}

function ZoomWatcher({ onZoom }) {
  const map = useMapEvents({ zoomend: () => onZoom(map.getZoom()) });
  useEffect(() => { onZoom(map.getZoom()); }, [map, onZoom]);
  return null;
}

// Below this zoom, stations overlap, so they shrink to coloured dots
const LABEL_MIN_ZOOM = 12;
const CARTO_KEY = process.env.NEXT_PUBLIC_CARTO_API_KEY;

function stationIcon(aqi, selected, compact) {
  const color = getAqiColor(aqi);
  if (compact) {
    return L.divIcon({
      className: 'station-marker-wrap',
      html: `<div class="station-dot${selected ? ' selected' : ''}" style="--c:${color}"></div>`,
      iconSize: [14, 14],
      iconAnchor: [7, 7],
    });
  }
  return L.divIcon({
    className: 'station-marker-wrap',
    html: `<div class="station-marker${selected ? ' selected' : ''}" style="--c:${color}">
             <span class="station-pulse"></span><span class="station-value">${Math.round(aqi)}</span>
           </div>`,
    iconSize: [40, 24],
    iconAnchor: [20, 12],
  });
}

export default function PredictionMap({
  wards = [],
  source = null,
  timeline: timelineData = null,
  onWardClick,
  selectedWardId = null,
  height = 560,
  showVulnerable = false,
}) {
  // A slow/failed timeline request must not combine an old forecast with new inputs.
  const timeline = timelineData?.observed_at === source?.observed_at ? timelineData : null;
  const [geo, setGeo] = useState(null);
  const [hourIdx, setHourIdx] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [hover, setHover] = useState(null);
  const [pinnedWard, setPinnedWard] = useState(null);
  const [zoom, setZoom] = useState(11);
  const [vulnData, setVulnData] = useState([]);
  const [vulnNote, setVulnNote] = useState(null);
  const [showVuln, setShowVuln] = useState({ hospital: true, school: true, elderly_care: false });
  const light = useSyncExternalStore(subscribeTheme, isLightTheme, () => false);
  const geoRef = useRef(null);
  const wardValuesRef = useRef(new Map());

  const horizon = timeline?.timestamps?.length ?? 0;

  useEffect(() => {
    loadWardGeometry().then(setGeo).catch((err) => console.error('Failed to load ward geometry:', err));
  }, []);

  useEffect(() => {
    if (!showVulnerable) return;
    // Same dataset the enforcement counts use, with per-record provenance
    getVulnerable('delhi')
      .then((data) => {
        setVulnData(data.locations ?? []);
        setVulnNote(data.data_note ?? null);
      })
      .catch(() => {});
  }, [showVulnerable]);

  // Auto-play the forecast timeline
  useEffect(() => {
    if (!playing || !horizon) return;
    const id = setInterval(() => {
      setHourIdx((h) => (h >= horizon ? 0 : h + 1));
    }, PLAY_INTERVAL_MS);
    return () => clearInterval(id);
  }, [playing, horizon]);

  // Station values at the selected hour (0 = now, n = model prediction for +n h)
  const stations = useMemo(() => wards.map((w) => {
    const series = timeline?.wards?.[w.ward_id];
    const value = hourIdx === 0 || !series ? w.current_aqi : series[hourIdx - 1];
    const pm25 = hourIdx === 0 ? w.current_pm25 : aqiToPm25(value);
    return { ...w, value, pm25 };
  }), [wards, timeline, hourIdx]);

  // City-average curve for the timeline sparkline
  const cityCurve = useMemo(() => {
    if (!wards.length) return [];
    const now = wards.reduce((s, w) => s + w.current_aqi, 0) / wards.length;
    if (!timeline?.wards) return [now];
    const ids = Object.keys(timeline.wards);
    const hours = timeline.timestamps.map((_, i) => ids.reduce((s, id) => s + timeline.wards[id][i], 0) / ids.length);
    return [now, ...hours];
  }, [wards, timeline]);

  // Interpolate every ward polygon from the stations
  const wardValues = useMemo(() => {
    const out = new Map();
    if (!geo) return out;
    geo.features.forEach((f) => {
      out.set(f.properties.Ward_Name, wardEstimate(f.properties.centroid, stations));
    });
    return out;
  }, [geo, stations]);

  // Push new colours into the existing Leaflet layers (no re-mount while scrubbing)
  useEffect(() => {
    wardValuesRef.current = wardValues;
    geoRef.current?.eachLayer((layer) => {
      const v = wardValues.get(layer.feature.properties.Ward_Name)?.aqi;
      layer.setStyle({ fillColor: aqiRampColor(v), color: aqiRampColor(v) });
    });
  }, [wardValues]);

  const nearestStation = (point) => {
    let best = null, bestD = Infinity;
    stations.forEach((s) => {
      const d = Math.hypot(s.lat - point.lat, s.lon - point.lon);
      if (d < bestD) { bestD = d; best = s; }
    });
    return best;
  };

  function onEachFeature(feature, layer) {
    layer.on({
      mouseover: (e) => {
        e.target.setStyle({ weight: 2, fillOpacity: 0.78 });
        e.target.bringToFront();
        setHover({ name: feature.properties.Ward_Name, centroid: feature.properties.centroid });
      },
      mouseout: (e) => {
        e.target.setStyle({ weight: 0.6, fillOpacity: 0.58 });
        setHover(null);
      },
      click: () => {
        setPinnedWard({ name: feature.properties.Ward_Name, centroid: feature.properties.centroid });
      },
    });
  }

  const initialStyle = (feature) => {
    const v = wardValuesRef.current.get(feature.properties.Ward_Name)?.aqi;
    return { fillColor: aqiRampColor(v), color: aqiRampColor(v), weight: 0.6, opacity: 0.55, fillOpacity: 0.58 };
  };

  const cityNow = cityCurve[hourIdx] ?? cityCurve[0];
  const sample = source?.data_source === 'offline-sample';
  const stale = source?.freshness?.status === 'stale';
  const observedLabel = source?.observed_at ? new Date(source.observed_at).toLocaleString('en-IN', {
    timeZone: 'Asia/Kolkata', day: 'numeric', month: 'short', year: 'numeric', hour: 'numeric', minute: '2-digit',
  }) + ' IST' : 'Time unavailable';
  const timeLabel = hourIdx === 0 || !timeline ? observedLabel : formatHourLabel(timeline.timestamps[hourIdx - 1]);
  const activeWard = pinnedWard || hover;
  const estimate = activeWard ? wardValues.get(activeWard.name) : null;
  const hoverValue = estimate?.aqi;
  const hoverStation = activeWard ? nearestStation(activeWard.centroid) : null;

  const tiles = light
    ? { base: 'light_nolabels', labels: 'light_only_labels' }
    : { base: 'dark_nolabels', labels: 'dark_only_labels' };

  return (
    <div className="pmap" style={{ '--pmap-h': `${height}px` }}>
      {!geo && <div className="pmap-loading skeleton" />}

      <MapContainer
        center={DELHI_CENTER}
        zoom={10}
        minZoom={9}
        zoomSnap={0.25}
        zoomControl={false}
        scrollWheelZoom
        style={{ height: '100%', width: '100%' }}
      >
        <TileLayer
          key={tiles.base}
          url={CARTO_KEY ? `https://{s}.basemaps.cartocdn.com/${tiles.base}/{z}/{x}/{y}{r}.png?key=${encodeURIComponent(CARTO_KEY)}` : "https://tile.openstreetmap.org/{z}/{x}/{y}.png"}
          attribution={'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' + (CARTO_KEY ? ' &copy; CARTO' : '')}
        />
        {geo && (
          <GeoJSON ref={geoRef} data={geo} style={initialStyle} onEachFeature={onEachFeature} />
        )}
        <FitToCity geo={geo} />
        <ZoomWatcher onZoom={setZoom} />
        <ZoomControl position="bottomright" />
        {CARTO_KEY && <Pane name="labels" style={{ zIndex: 450, pointerEvents: 'none' }}>
          <TileLayer key={tiles.labels} url={`https://{s}.basemaps.cartocdn.com/${tiles.labels}/{z}/{x}/{y}{r}.png?key=${encodeURIComponent(CARTO_KEY)}`} />
        </Pane>}

        {showVulnerable && vulnData.filter((v) => showVuln[v.type]).map((v, i) => (
          <CircleMarker
            key={`v${i}`}
            center={[v.lat, v.lon]}
            radius={4}
            pathOptions={v.verified
              ? { fillColor: VULN_CONFIG[v.type]?.color, color: '#fff', weight: 1, fillOpacity: 0.95 }
              : { fillColor: VULN_CONFIG[v.type]?.color, color: VULN_CONFIG[v.type]?.color, weight: 1, fillOpacity: 0.25, dashArray: '2 2' }}
          >
            <Tooltip>
              {v.verified
                ? <>{v.name} · {v.ward_name}</>
                : <>Synthetic placeholder ({VULN_CONFIG[v.type]?.label.toLowerCase()}), not a real facility</>}
            </Tooltip>
          </CircleMarker>
        ))}

        {stations.map((s) => (
          <Marker
            key={s.ward_id}
            title={`${s.ward_name}: AQI estimate ${Math.round(s.value)}`}
            alt={`${s.ward_name}: AQI estimate ${Math.round(s.value)}`}
            position={[s.lat, s.lon]}
            icon={stationIcon(s.value, s.ward_id === selectedWardId, zoom < LABEL_MIN_ZOOM && s.ward_id !== selectedWardId)}
            eventHandlers={{ click: () => onWardClick && onWardClick(s) }}
          >
            <Tooltip direction="top" offset={[0, -10]}>
              <strong>{s.ward_name}</strong> · AQI {Math.round(s.value)} ({getAqiLabel(s.value)})
              {s.ground_station && <><br /><span style={{ opacity: 0.7 }}>CPCB: {s.ground_station}</span></>}
            </Tooltip>
          </Marker>
        ))}
      </MapContainer>

      {/* Headline: city AQI at the selected hour */}
      <div className="pmap-panel pmap-headline">
        <p className="pmap-eyebrow">{sample ? 'Historical sample' : stale ? 'Stale estimate' : hourIdx === 0 ? 'Air quality estimate' : 'Predicted air quality'}</p>
        <div className="pmap-headline-row">
          <span className="pmap-big" style={{ color: getAqiColor(cityNow) }}>{Math.round(cityNow ?? 0)}</span>
          <div>
            <span className="pmap-band" style={{ background: `${getAqiColor(cityNow)}22`, color: getAqiColor(cityNow) }}>
              {getAqiLabel(cityNow)}
            </span>
            <p className="pmap-sub">Station mean · {timeLabel}{hourIdx > 0 && ` · +${hourIdx}h`}</p>
          </div>
        </div>
      </div>

      {/* Legend + overlays */}
      <div className="pmap-panel pmap-legend">
        <p className="pmap-eyebrow">PM2.5 AQI estimate</p>
        <p className="pmap-sub">Polygons: interpolated estimates. Dots: station locations.</p>
        <div className="pmap-ramp" />
        <div className="pmap-ramp-labels"><span>0</span><span>100</span><span>200</span><span>300</span><span>400</span><span>500</span></div>
        {showVulnerable && (
          <div className="pmap-vuln">
            {Object.entries(VULN_CONFIG).map(([type, cfg]) => (
              <button
                key={type}
                className={`pmap-chip${showVuln[type] ? ' on' : ''}`}
                style={{ '--c': cfg.color }}
                onClick={() => setShowVuln((p) => ({ ...p, [type]: !p[type] }))}
              >
                <span className="dot" />{cfg.label}
              </button>
            ))}
            {vulnNote && <p className="pmap-vuln-note">{vulnNote}</p>}
          </div>
        )}
      </div>

      {/* Hovered ward */}
      {activeWard && (
        <div className={`pmap-panel pmap-hover${pinnedWard ? ' pmap-pinned' : ''}`}>
          <p className="pmap-hover-name">{activeWard.name.toLowerCase()}</p>
          <div className="pmap-headline-row">
            <span className="pmap-mid" style={{ color: getAqiColor(hoverValue) }}>{hoverValue == null ? '—' : Math.round(hoverValue)}</span>
            <span className="pmap-sub">{getAqiLabel(hoverValue)}</span>
          </div>
          <p className="pmap-sub">{estimate?.count ? `${estimate.count} nearby inputs; nearest ${estimate.nearestKm.toFixed(1)} km. ${estimate.groundCount} ground-calibrated.` : 'No inputs within 20 km.'}</p>
          <p className="pmap-sub">{sample ? 'Historical sample, not current.' : 'Spatial uncertainty has not been validated.'}</p>
          {hoverStation && <button onClick={() => onWardClick?.(hoverStation)}>View nearby station: {hoverStation.ward_name}</button>}
          {pinnedWard && <button aria-label="Close ward estimate" onClick={() => setPinnedWard(null)}>Close</button>}
        </div>
      )}

      {/* Forecast timeline */}
      {horizon > 0 && (
        <div className="pmap-panel pmap-timeline">
          <button
            className="pmap-play"
            onClick={() => setPlaying((p) => !p)}
            aria-label={playing ? 'Pause forecast animation' : 'Play forecast animation'}
          >
            {playing ? (
              <svg width="14" height="14" viewBox="0 0 14 14"><rect x="2" y="1" width="3.5" height="12" rx="1" fill="currentColor" /><rect x="8.5" y="1" width="3.5" height="12" rx="1" fill="currentColor" /></svg>
            ) : (
              <svg width="14" height="14" viewBox="0 0 14 14"><path d="M3 1.5v11l9.5-5.5z" fill="currentColor" /></svg>
            )}
          </button>
          <div className="pmap-track">
            <TimelineSpark values={cityCurve} active={hourIdx} />
            <input
              type="range"
              min={0}
              max={horizon}
              value={hourIdx}
              onChange={(e) => { setPlaying(false); setHourIdx(Number(e.target.value)); }}
              aria-label="Forecast hour"
            />
            <div className="pmap-ticks">
              <span>Base time</span><span>+24h</span><span>+48h</span><span>+72h</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function TimelineSpark({ values, active }) {
  if (values.length < 2) return null;
  const W = 600, H = 34;
  const max = Math.max(...values), min = Math.min(...values);
  const range = max - min || 1;
  const x = (i) => (i / (values.length - 1)) * W;
  const y = (v) => H - 3 - ((v - min) / range) * (H - 6);
  const d = values.map((v, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ');
  return (
    <div className="pmap-spark">
    <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
      <defs>
        <linearGradient id="spark-fill" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0" stopColor="var(--accent-primary)" stopOpacity="0.35" />
          <stop offset="1" stopColor="var(--accent-primary)" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={`${d} L${W},${H} L0,${H} Z`} fill="url(#spark-fill)" />
      <path d={d} fill="none" stroke="var(--accent-primary)" strokeWidth="1.6" vectorEffect="non-scaling-stroke" />
    </svg>
      <span
        className="pmap-spark-dot"
        style={{ left: `${(x(active) / W) * 100}%`, top: `${(y(values[active]) / H) * 100}%`, background: getAqiColor(values[active]) }}
      />
    </div>
  );
}

