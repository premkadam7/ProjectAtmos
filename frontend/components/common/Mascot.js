'use client';

/* ================================================================
   ATMOS MASCOT — "Puff"
   A round, breathing character whose face and colour react to
   the live AQI. Good air = wide-eyed and grinning. Severe air =
   wearing a mask, eyes squeezed shut. Built as pure SVG so it's
   cheap to animate and easy to re-skin later.

   Usage:
     <Mascot aqi={cityAqi} size={180} />
================================================================ */

function moodForAqi(aqi) {
  if (aqi <= 50)  return 'great';
  if (aqi <= 100) return 'good';
  if (aqi <= 200) return 'meh';
  if (aqi <= 300) return 'bad';
  if (aqi <= 400) return 'rough';
  return 'severe';
}

const MOOD_COLOR = {
  great:  '#4ade80',
  good:   '#a3e635',
  meh:    '#facc15',
  bad:    '#fb923c',
  rough:  '#f97316',
  severe: '#ff8f6b',
};

const MOOD_FACE = {
  great:  { eye: 'M -18 -6 Q -14 -14 -10 -6 M 10 -6 Q 14 -14 18 -6', mouth: 'M -14 10 Q 0 24 14 10', wearMask: false },
  good:   { eye: 'M -18 -4 Q -14 -10 -10 -4 M 10 -4 Q 14 -10 18 -4', mouth: 'M -12 10 Q 0 18 12 10', wearMask: false },
  meh:    { eye: 'M -16 -5 L -10 -5 M 10 -5 L 16 -5', mouth: 'M -10 12 L 10 12', wearMask: false },
  /* worried, angled-down eyebrows for unhealthy moods — reads as concerned, not sleepy */
  bad:    { eye: 'M -17 -8 L -9 -3 M 9 -3 L 17 -8', wearMask: true },
  rough:  { eye: 'M -17 -9 L -9 -3 M 9 -3 L 17 -9', wearMask: true },
  severe: { eye: 'M -17 -10 L -9 -3 M 9 -3 L 17 -10', wearMask: true },
};

export default function Mascot({ aqi = 100, size = 180, className = '' }) {
  const mood = moodForAqi(aqi);
  const color = MOOD_COLOR[mood];
  const face = MOOD_FACE[mood];

  return (
    <svg
      className={`mascot-breathe ${className}`}
      width={size}
      height={size}
      viewBox="-60 -60 120 120"
      style={{ overflow: 'visible' }}
    >
      {/* soft glow halo */}
      <circle r="46" fill={color} opacity="0.16" className="mascot-halo" />

      {/* ambient particles, colour-coded to mood */}
      {[...Array(3)].map((_, i) => (
        <circle
          key={i}
          className="mascot-particle"
          style={{ animationDelay: `${i * 0.9}s` }}
          cx={-26 + i * 26}
          cy={-40}
          r="3"
          fill={color}
          opacity="0.5"
        />
      ))}

      {/* body */}
      <circle r="38" fill={color} className="mascot-body" />
      <circle r="38" fill="url(#mascot-shine)" />

      <defs>
        <radialGradient id="mascot-shine" cx="35%" cy="28%" r="65%">
          <stop offset="0%" stopColor="#ffffff" stopOpacity="0.35" />
          <stop offset="100%" stopColor="#ffffff" stopOpacity="0" />
        </radialGradient>
      </defs>

      {/* face */}
      <g stroke="#1a1a1a" strokeWidth="2.5" strokeLinecap="round" fill="none">
        <path d={face.eye} />
        {!face.wearMask && <path d={face.mouth} />}
      </g>

      {/* mask for unhealthy moods */}
      {face.wearMask && (
        <g>
          <path
            d="M -20 6 Q 0 22 20 6 L 20 16 Q 0 30 -20 16 Z"
            fill="#f8fafc"
            stroke="#cbd5e1"
            strokeWidth="1.5"
          />
          <path d="M -20 11 L 20 11" stroke="#cbd5e1" strokeWidth="1" />
        </g>
      )}

      {/* little feet, only visible when happy */}
      {(mood === 'great' || mood === 'good') && (
        <g className="mascot-feet">
          <ellipse cx="-14" cy="40" rx="7" ry="4" fill={color} />
          <ellipse cx="14" cy="40" rx="7" ry="4" fill={color} />
        </g>
      )}
    </svg>
  );
}