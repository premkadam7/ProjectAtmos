// Estimate concentration first: AQI is a nonlinear transform, not an additive quantity.
const PM25_BANDS = [[0,30,0,50],[30,60,50,100],[60,90,100,200],[90,120,200,300],[120,250,300,400],[250,500,400,500]];
export function pm25ToAqi(pm) {
  if (!Number.isFinite(pm)) return null;
  const [lo, hi, a, b] = PM25_BANDS.find((v) => pm <= v[1]) || PM25_BANDS.at(-1);
  return Math.max(0, Math.min(500, a + (pm-lo)*(b-a)/(hi-lo)));
}
export function aqiToPm25(aqi) {
  if (!Number.isFinite(aqi)) return null;
  const [lo, hi, a, b] = PM25_BANDS.find((v) => aqi <= v[3]) || PM25_BANDS.at(-1);
  return Math.max(0, lo + (aqi-a)*(hi-lo)/(b-a));
}
export function wardEstimate(point, samples, { maxDistanceKm = 20, k = 6 } = {}) {
  const nearby = samples.filter(s => Number.isFinite(s.pm25)).map(s => ({
    ...s,
    distance: Math.hypot((s.lat-point.lat)*111.32,
      (s.lon-point.lon)*111.32*Math.cos(point.lat*Math.PI/180)),
  })).filter(s => s.distance <= maxDistanceKm).sort((a,b) => a.distance-b.distance).slice(0,k);
  if (!nearby.length) return { aqi: null, count: 0, nearestKm: null };
  const weights = nearby.map(s => 1/Math.max(s.distance,0.2)**2);
  const pm25 = nearby.reduce((sum,s,i) => sum+s.pm25*weights[i],0)/weights.reduce((a,b)=>a+b,0);
  return { aqi: pm25ToAqi(pm25), pm25, count: nearby.length, nearestKm: nearby[0].distance,
    groundCount: nearby.filter(s => s.ground_station).length };
}
