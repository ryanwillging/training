'use client';

import { useEffect, useState } from 'react';

interface GaugeProps {
  value: number;
  max?: number;
  min?: number;
  label?: string;
  unit?: string;
  color?: string;
  size?: number;
  className?: string;
}

export function Gauge({
  value,
  max = 100,
  min = 0,
  label,
  unit,
  color = '#1976d2',
  size = 120,
  className,
}: GaugeProps) {
  const [animated, setAnimated] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setAnimated(true), 100);
    return () => clearTimeout(timer);
  }, []);

  const normalizedValue = Math.min(max, Math.max(min, value));
  const percentage = ((normalizedValue - min) / (max - min)) * 100;

  // SVG arc calculations
  const strokeWidth = 10;
  const radius = (size - strokeWidth) / 2;
  const circumference = Math.PI * radius; // Semi-circle
  const offset = circumference - (percentage / 100) * circumference;

  // Determine color based on value (for auto-coloring based on wellness)
  const getColor = () => {
    if (color !== 'auto') return color;
    if (percentage >= 70) return '#2e7d32'; // Success
    if (percentage >= 40) return '#ed6c02'; // Warning
    return '#d32f2f'; // Error
  };

  return (
    <div className={className}>
      <div className="relative" style={{ width: size, height: size / 2 + 20 }}>
        <svg width={size} height={size / 2 + 20} viewBox={`0 0 ${size} ${size / 2 + 20}`}>
          {/* Background arc */}
          <path
            d={`M ${strokeWidth / 2} ${size / 2} A ${radius} ${radius} 0 0 1 ${size - strokeWidth / 2} ${size / 2}`}
            fill="none"
            stroke="#e5e7eb"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
          />
          {/* Value arc */}
          <path
            d={`M ${strokeWidth / 2} ${size / 2} A ${radius} ${radius} 0 0 1 ${size - strokeWidth / 2} ${size / 2}`}
            fill="none"
            stroke={getColor()}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={animated ? offset : circumference}
            style={{
              transition: 'stroke-dashoffset 1s ease-out',
            }}
          />
        </svg>

        {/* Value display */}
        <div className="absolute inset-0 flex flex-col items-center justify-end pb-1">
          <span className="text-2xl font-medium text-gray-900">
            {Math.round(normalizedValue)}
            {unit && <span className="text-sm text-gray-500 ml-0.5">{unit}</span>}
          </span>
        </div>
      </div>

      {label && (
        <p className="text-center text-xs text-gray-500 mt-1">{label}</p>
      )}
    </div>
  );
}
