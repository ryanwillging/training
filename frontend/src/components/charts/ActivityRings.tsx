'use client';

import { useEffect, useState } from 'react';

interface Ring {
  value: number;
  max: number;
  color: string;
  label: string;
}

interface ActivityRingsProps {
  rings: Ring[];
  size?: number;
  strokeWidth?: number;
  className?: string;
}

export function ActivityRings({
  rings,
  size = 200,
  strokeWidth = 16,
  className,
}: ActivityRingsProps) {
  const [animated, setAnimated] = useState(false);

  useEffect(() => {
    // Trigger animation after mount
    const timer = setTimeout(() => setAnimated(true), 100);
    return () => clearTimeout(timer);
  }, []);

  const center = size / 2;
  const gapBetweenRings = 4;

  return (
    <div className={className}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        {rings.map((ring, index) => {
          // Calculate radius for each ring (outer to inner)
          const radius = center - strokeWidth / 2 - index * (strokeWidth + gapBetweenRings);
          const circumference = 2 * Math.PI * radius;
          const percentage = Math.min(100, (ring.value / ring.max) * 100);
          const offset = circumference - (percentage / 100) * circumference;

          return (
            <g key={ring.label}>
              {/* Background ring */}
              <circle
                cx={center}
                cy={center}
                r={radius}
                fill="none"
                stroke="#e5e7eb"
                strokeWidth={strokeWidth}
                opacity={0.3}
              />
              {/* Progress ring */}
              <circle
                cx={center}
                cy={center}
                r={radius}
                fill="none"
                stroke={ring.color}
                strokeWidth={strokeWidth}
                strokeLinecap="round"
                strokeDasharray={circumference}
                strokeDashoffset={animated ? offset : circumference}
                transform={`rotate(-90 ${center} ${center})`}
                style={{
                  transition: 'stroke-dashoffset 1s ease-out',
                }}
              />
            </g>
          );
        })}
      </svg>

      {/* Legend */}
      <div className="flex flex-col gap-2 mt-4">
        {rings.map((ring) => {
          const percentage = Math.min(100, Math.round((ring.value / ring.max) * 100));
          return (
            <div key={ring.label} className="flex items-center gap-3">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: ring.color }}
              />
              <span className="text-sm text-gray-600 flex-1">{ring.label}</span>
              <span className="text-sm font-medium">{percentage}%</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
