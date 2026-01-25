'use client';

import { useQuery } from '@tanstack/react-query';
import { Card, CardHeader, CardTitle, CardContent, LoadingState, Progress } from '@/components/ui';
import { planApi } from '@/lib/api';

export function ThisWeekWidget() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['week-summary'],
    queryFn: () => planApi.getWeekSummary(),
  });

  const { data: status } = useQuery({
    queryKey: ['plan-status'],
    queryFn: planApi.getStatus,
  });

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>This Week</CardTitle>
        </CardHeader>
        <CardContent>
          <LoadingState message="Loading week data..." />
        </CardContent>
      </Card>
    );
  }

  if (error || !data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>This Week</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-500">Unable to load week data</p>
        </CardContent>
      </Card>
    );
  }

  const workouts = data.workouts || [];
  const completed = workouts.filter((w) => w.status === 'completed').length;
  const total = workouts.length;
  const adherencePct = total > 0 ? Math.round((completed / total) * 100) : 0;

  // Calculate total volume (minutes)
  const totalVolume = workouts
    .filter((w) => w.status === 'completed')
    .reduce((sum, w) => sum + (w.duration_minutes || 0), 0);

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>This Week</CardTitle>
        <span className="text-sm text-gray-500">
          Week {data.week_number} of 24
        </span>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Adherence */}
          <div>
            <div className="flex justify-between items-center mb-1">
              <span className="text-sm text-gray-600">Adherence</span>
              <span className="text-sm font-medium">
                {completed}/{total} workouts
              </span>
            </div>
            <Progress value={adherencePct} />
          </div>

          {/* Volume */}
          <div className="flex justify-between items-center pt-2 border-t border-gray-100">
            <span className="text-sm text-gray-600">Volume completed</span>
            <span className="text-lg font-medium">
              {totalVolume > 60
                ? `${Math.floor(totalVolume / 60)}h ${totalVolume % 60}m`
                : `${totalVolume}min`}
            </span>
          </div>

          {/* Test week indicator */}
          {data.is_test_week && (
            <div className="flex items-center gap-2 pt-2 border-t border-gray-100">
              <span className="text-amber-600 text-lg">🎯</span>
              <span className="text-sm text-amber-700 font-medium">
                Test Week - Performance testing scheduled
              </span>
            </div>
          )}

          {/* Plan progress */}
          {status && (
            <div className="pt-2 border-t border-gray-100">
              <div className="flex justify-between items-center mb-1">
                <span className="text-sm text-gray-600">Plan Progress</span>
                <span className="text-sm text-gray-500">
                  {status.days_until_end} days remaining
                </span>
              </div>
              <Progress
                value={status.current_week}
                max={status.total_weeks}
                variant="success"
              />
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
