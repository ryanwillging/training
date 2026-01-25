'use client';

import {
  BarChart as RechartsBarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';

interface DataPoint {
  [key: string]: string | number | null | undefined;
}

interface BarChartProps {
  data: DataPoint[];
  xKey: string;
  yKey: string;
  color?: string;
  colors?: string[];
  height?: number;
  showGrid?: boolean;
  showAxis?: boolean;
}

export function BarChart({
  data,
  xKey,
  yKey,
  color = '#1976d2',
  colors,
  height = 200,
  showGrid = true,
  showAxis = true,
}: BarChartProps) {
  if (!data || data.length === 0) {
    return (
      <div
        className="flex items-center justify-center bg-gray-50 rounded-lg"
        style={{ height }}
      >
        <p className="text-sm text-gray-500">No data available</p>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <RechartsBarChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
        {showGrid && <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" vertical={false} />}
        {showAxis && (
          <>
            <XAxis
              dataKey={xKey}
              tick={{ fontSize: 12, fill: '#6b7280' }}
              tickLine={false}
              axisLine={{ stroke: '#e5e7eb' }}
            />
            <YAxis
              tick={{ fontSize: 12, fill: '#6b7280' }}
              tickLine={false}
              axisLine={false}
              width={40}
            />
          </>
        )}
        <Tooltip
          contentStyle={{
            backgroundColor: 'white',
            border: '1px solid #e5e7eb',
            borderRadius: '8px',
            fontSize: '14px',
          }}
        />
        <Bar dataKey={yKey} radius={[4, 4, 0, 0]}>
          {colors
            ? data.map((_, index) => (
                <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
              ))
            : data.map((_, index) => <Cell key={`cell-${index}`} fill={color} />)}
        </Bar>
      </RechartsBarChart>
    </ResponsiveContainer>
  );
}
