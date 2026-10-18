// Shared AQI scale (Indian NAQI), colours and spatial helpers.

export const AQI_BANDS = [
  { max: 50,  label: 'Good',         color: '#22c55e', range: '0 – 50' },
  { max: 100, label: 'Satisfactory', color: '#84cc16', range: '51 – 100' },
  { max: 200, label: 'Moderate',     color: '#eab308', range: '101 – 200' },
  { max: 300, label: 'Poor',         color: '#f97316', range: '201 – 300' },
  { max: 400, label: 'Very Poor',    color: '#ef4444', range: '301 – 400' },
  { max: Infinity, label: 'Severe',  color: '#a21caf', range: '401 – 500' },
];

export function aqiBand(aqi) {
  if (aqi == null || Number.isNaN(aqi)) return null;
  return AQI_BANDS.find((b) => aqi <= b.max);
}

export function getAqiColor(aqi) {
  return aqiBand(aqi)?.color ?? '#6b7280';
}

export function getAqiLabel(aqi) {
  return aqiBand(aqi)?.label ?? '—';
}

// Continuous colour for maps: blends between band colours so neighbouring
// wards with similar AQI don't jump between flat swatches.
const RAMP = [
  [0, [34, 197, 94]], [50, [34, 197, 94]], [100, [132, 204, 22]], [200, [234, 179, 8]],
  [300, [249, 115, 22]], [400, [239, 68, 68]], [500, [162, 28, 175]],
];

export function aqiRampColor(aqi) {
  if (aqi == null) return '#6b7280';
  const v = Math.max(0, Math.min(500, aqi));
  for (let i = 0; i < RAMP.length - 1; i++) {
    const [a, ca] = RAMP[i];
    const [b, cb] = RAMP[i + 1];
    if (v <= b) {
      const t = (v - a) / (b - a || 1);
      const c = ca.map((x, k) => Math.round(x + (cb[k] - x) * t));
      return `rgb(${c[0]}, ${c[1]}, ${c[2]})`;
    }
  }
  return `rgb(${RAMP[RAMP.length - 1][1].join(', ')})`;
}

export function polygonCentroid(geometry) {
  const ring = geometry.type === 'Polygon' ? geometry.coordinates[0] : geometry.coordinates[0][0];
  let x = 0, y = 0;
  ring.forEach(([lon, lat]) => { x += lon; y += lat; });
  return { lat: y / ring.length, lon: x / ring.length };
}

function distanceKm(a, b) {
  const dLat = (b.lat - a.lat) * 111.32;
  const dLon = (b.lon - a.lon) * 111.32 * Math.cos(((a.lat + b.lat) / 2) * Math.PI / 180);
  return Math.hypot(dLat, dLon);
}

/**
 * Inverse-distance-weighted estimate at `point` from `samples` ({lat, lon, value}).
 * Uses the nearest `k` samples so distant stations don't flatten local hotspots.
 */
export function idw(point, samples, { power = 2, k = 6 } = {}) {
  const nearest = samples
    .filter((s) => s.value != null)
    .map((s) => ({ ...s, d: distanceKm(point, s) }))
    .sort((a, b) => a.d - b.d)
    .slice(0, k);
  if (!nearest.length) return null;
  if (nearest[0].d < 0.2) return nearest[0].value;
  let num = 0, den = 0;
  nearest.forEach((s) => {
    const w = 1 / Math.pow(s.d, power);
    num += w * s.value;
    den += w;
  });
  return num / den;
}

// Ward boundaries are shared by every map; fetch them once per page load.
let wardGeometryPromise = null;
export function loadWardGeometry() {
  if (!wardGeometryPromise) {
    wardGeometryPromise = fetch('/data/delhi_wards.geojson')
      .then((r) => r.json())
      .then((data) => {
        data.features.forEach((f) => { f.properties.centroid = polygonCentroid(f.geometry); });
        return data;
      })
      .catch((err) => {
        wardGeometryPromise = null;
        throw err;
      });
  }
  return wardGeometryPromise;
}

export function formatHourLabel(iso) {
  const d = new Date(iso);
  return d.toLocaleString('en-IN', { weekday: 'short', hour: 'numeric', hour12: true });
}

export const SOURCE_INFO = {
  live: { label: 'Live', tone: '#22c55e' },
  'model-only': { label: 'Live (model only)', tone: '#eab308' },
  'offline-sample': { label: 'Offline sample', tone: '#f97316' },
};
