'use client';

/* Small inline face — no body — for use inside list rows, pills, strips.
   Same mood thresholds as Mascot.js so the "character" stays consistent
   everywhere it shows up. */

function moodForAqi(aqi) {
  if (aqi <= 50)  return 'great';
  if (aqi <= 100) return 'good';
  if (aqi <= 200) return 'meh';
  if (aqi <= 300) return 'bad';
  if (aqi <= 400) return 'rough';
  return 'severe';
}

const MOOD_COLOR = {
  great: '#4ade80', good: '#a3e635', meh: '#facc15',
  bad: '#fb923c', rough: '#f97316', severe: '#ff8f6b',
};

const MOOD_FACE = {
  great:  { eye: 'M -6 -2 Q -4 -5 -2 -2 M 2 -2 Q 4 -5 6 -2', mouth: 'M -5 3 Q 0 8 5 3' },
  good:   { eye: 'M -6 -1 Q -4 -3 -2 -1 M 2 -1 Q 4 -3 6 -1', mouth: 'M -4 3 Q 0 6 4 3' },
  meh:    { eye: 'M -6 -1 L -2 -1 M 2 -1 L 6 -1', mouth: 'M -4 4 L 4 4' },
  bad:    { eye: 'M -6 0 L -2 0 M 2 0 L 6 0', mouth: 'M -4 5 Q 0 2 4 5' },
  rough:  { eye: 'M -6 1 L -2 1 M 2 1 L 6 1', mouth: 'M -4 5 Q 0 2 4 5' },
  severe: { eye: 'M -6 1 L -2 1 M 2 1 L 6 1', mouth: 'M -4 5 Q 0 2 4 5' },
};

export default function MiniFace({ aqi, size = 22 }) {
  const mood = moodForAqi(aqi);
  const color = MOOD_COLOR[mood];
  const face = MOOD_FACE[mood];

  return (
    <svg width={size} height={size} viewBox="-11 -11 22 22" style={{ flexShrink: 0 }}>
      <circle r="10" fill={color} opacity="0.9" />
      <g stroke="#1a1a1a" strokeWidth="1.4" strokeLinecap="round" fill="none">
        <path d={face.eye} />
        <path d={face.mouth} />
      </g>
    </svg>
  );
}