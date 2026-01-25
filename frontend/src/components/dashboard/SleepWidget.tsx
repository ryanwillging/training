'use client';

import { useQuery } from '@tanstack/react-query';
import { Card, CardHeader, CardTitle, CardContent, LoadingState } from '@/components/ui';
import { wellnessApi } from '@/lib/api';
import { Moon, Clock, Activity } from 'lucide-react';

export function SleepWidget() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['wellness-latest'],
    queryFn: wellnessApi.getLatest,
  });

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Sleep Last Night</CardTitle>
        </CardHeader>
        <CardContent>
          <LoadingState message="Loading sleep data..." />
        </CardContent>
      </Card>
    );
  }

  if (error || !data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Sleep Last Night</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-500 text-center py-6">
            No sleep data available
          </p>
        </CardContent>
      </Card>
    );
  }

  const formatHours = (hours: number | null) => {
    if (hours === null) return '--';
    const h = Math.floor(hours);
    const m = Math.round((hours - h) * 60);
    return `${h}h ${m}m`;
  };

  const formatMinutes = (mins: number | null) => {
    if (mins === null) return '--';
    return `${mins}m`;
  };

  // Sleep quality color
  const getScoreColor = (score: number | null) => {
    if (score === null) return 'text-gray-400';
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-amber-600';
    return 'text-red-600';
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Sleep Last Night</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Main stats */}
          <div className="flex items-center justify-around">
            <div className="text-center">
              <div className="flex items-center justify-center gap-1 text-gray-500 mb-1">
                <Clock className="w-4 h-4" />
                <span className="text-xs">Duration</span>
              </div>
              <p className="text-2xl font-semibold">
                {formatHours(data.sleep_duration_hours)}
              </p>
            </div>
            <div className="text-center">
              <div className="flex items-center justify-center gap-1 text-gray-500 mb-1">
                <Activity className="w-4 h-4" />
                <span className="text-xs">Score</span>
              </div>
              <p className={`text-2xl font-semibold ${getScoreColor(data.sleep_score)}`}>
                {data.sleep_score ?? '--'}
              </p>
            </div>
          </div>

          {/* Sleep stages */}
          <div className="grid grid-cols-3 gap-2 pt-4 border-t border-gray-100">
            <div className="text-center">
              <p className="text-xs text-gray-500 mb-1">Deep</p>
              <p className="text-sm font-medium text-indigo-600">
                {formatMinutes(data.deep_sleep_minutes)}
              </p>
            </div>
            <div className="text-center">
              <p className="text-xs text-gray-500 mb-1">REM</p>
              <p className="text-sm font-medium text-purple-600">
                {formatMinutes(data.rem_sleep_minutes)}
              </p>
            </div>
            <div className="text-center">
              <p className="text-xs text-gray-500 mb-1">Light</p>
              <p className="text-sm font-medium text-blue-600">
                {formatMinutes(data.light_sleep_minutes)}
              </p>
            </div>
          </div>

          {/* Awake time */}
          {data.awake_minutes !== null && data.awake_minutes > 0 && (
            <div className="flex justify-between items-center pt-2 border-t border-gray-100">
              <span className="text-xs text-gray-500">Time awake</span>
              <span className="text-sm text-gray-600">
                {formatMinutes(data.awake_minutes)}
              </span>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
