'use client';

import { useEffect, useRef, useState } from 'react';

export default function CountUp({ value, duration = 900, decimals = 0, prefix = '', suffix = '' }) {
  const [display, setDisplay] = useState(0);
  const frameRef = useRef(null);
  const prevValueRef = useRef(0);

  useEffect(() => {
    const startValue = prevValueRef.current;
    const endValue = value;
    let startTime = null;

    function step(timestamp) {
      if (!startTime) startTime = timestamp;
      const progress = Math.min((timestamp - startTime) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
      setDisplay(startValue + (endValue - startValue) * eased);
      if (progress < 1) {
        frameRef.current = requestAnimationFrame(step);
      } else {
        prevValueRef.current = endValue;
      }
    }

    frameRef.current = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frameRef.current);
  }, [value, duration]);

  return <>{prefix}{display.toFixed(decimals)}{suffix}</>;
}