'use client';

import { useQuery } from '@tanstack/react-query';
import { Card, CardHeader, CardTitle, CardContent, LoadingState } from '@/components/ui';
import { Gauge } from '@/components/charts';
import { wellnessApi } from '@/lib/api';

export function RecoveryWidget() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['wellness-latest'],
    queryFn: wellnessApi.getLatest,
  });

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Recovery Status</CardTitle>
        </CardHeader>
        <CardContent>
          <LoadingState message="Loading wellness data..." />
        </CardContent>
      </Card>
    );
  }

  if (error || !data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Recovery Status</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-500 text-center py-6">
            No wellness data available
          </p>
        </CardContent>
      </Card>
    );
  }

  // Calculate readiness score based on available metrics
  const calculateReadiness = () => {
    const metrics: number[] = [];

    if (data.body_battery !== null) {
      metrics.push(data.body_battery); // Already 0-100
    }
    if (data.hrv !== null) {
      // Normalize HRV (assuming healthy range 20-80ms)
      const hrvScore = Math.min(100, Math.max(0, ((data.hrv - 20) / 60) * 100));
      metrics.push(hrvScore);
    }
    if (data.sleep_score !== null) {
      metrics.push(data.sleep_score); // Already 0-100
    }

    if (metrics.length === 0) return null;
    return Math.round(metrics.reduce((a, b) => a + b, 0) / metrics.length);
  };

  const readiness = calculateReadiness();

  return (
    <Card>
      <CardHeader>
        <CardTitle>Recovery Status</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-3 gap-4">
          <div className="flex flex-col items-center">
            <Gauge
              value={data.hrv ?? 0}
              max={80}
              min={20}
              label="HRV"
              unit="ms"
              color="auto"
              size={100}
            />
          </div>
          <div className="flex flex-col items-center">
            <Gauge
              value={data.resting_heart_rate ?? 60}
              max={80}
              min={40}
              label="RHR"
              unit="bpm"
              color="auto"
              size={100}
            />
          </div>
          <div className="flex flex-col items-center">
            <Gauge
              value={readiness ?? 0}
              max={100}
              min={0}
              label="Readiness"
              unit="%"
              color="auto"
              size={100}
            />
          </div>
        </div>

        {data.body_battery !== null && (
          <div className="mt-4 pt-4 border-t border-gray-100">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-500">Body Battery</span>
              <span className="text-lg font-medium">{data.body_battery}%</span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
