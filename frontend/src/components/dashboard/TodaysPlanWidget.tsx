'use client';

import { useQuery } from '@tanstack/react-query';
import { Card, CardHeader, CardTitle, CardContent, Badge, LoadingState } from '@/components/ui';
import { planApi, type ScheduledWorkout } from '@/lib/api';
import { WORKOUT_STYLES, formatDuration } from '@/lib/utils';

export function TodaysPlanWidget() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['upcoming', 1],
    queryFn: () => planApi.getUpcoming(1),
  });

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Today's Plan</CardTitle>
        </CardHeader>
        <CardContent>
          <LoadingState message="Loading today's workouts..." />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Today's Plan</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-500">Unable to load today's plan</p>
        </CardContent>
      </Card>
    );
  }

  const workouts = data?.workouts || [];
  const easternToday = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/New_York',
  }).format(new Date());
  const todayWorkouts = workouts.filter((w) => {
    return w.scheduled_date === easternToday;
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Today's Plan</CardTitle>
      </CardHeader>
      <CardContent>
        {todayWorkouts.length === 0 ? (
          <div className="text-center py-6">
            <div className="text-4xl mb-2">😴</div>
            <p className="text-sm text-gray-500">Rest day - no workouts scheduled</p>
          </div>
        ) : (
          <div className="space-y-3">
            {todayWorkouts.map((workout) => (
              <WorkoutItem key={workout.id} workout={workout} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function WorkoutItem({ workout }: { workout: ScheduledWorkout }) {
  const style = WORKOUT_STYLES[workout.workout_type] || {
    icon: '💪',
    label: workout.workout_type,
    color: '#666',
  };

  const getStatusBadge = () => {
    if (workout.status === 'completed') {
      return <Badge variant="success">Completed</Badge>;
    }
    if (workout.status === 'skipped') {
      return <Badge variant="warning">Skipped</Badge>;
    }
    if (workout.garmin_workout_id) {
      return <Badge variant="info">Synced</Badge>;
    }
    return null;
  };

  return (
    <div
      className="flex items-center gap-3 p-3 rounded-lg bg-gray-50"
      style={{ borderLeft: `4px solid ${style.color}` }}
    >
      <div
        className="w-10 h-10 rounded-full flex items-center justify-center text-xl"
        style={{ backgroundColor: `${style.color}20` }}
      >
        {style.icon}
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-medium text-gray-900 truncate">
          {workout.workout_name || style.label}
        </p>
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <span>Week {workout.week_number}</span>
          {workout.duration_minutes && (
            <>
              <span>·</span>
              <span>{formatDuration(workout.duration_minutes)}</span>
            </>
          )}
          {workout.is_test_week && (
            <Badge variant="warning" size="sm">
              TEST
            </Badge>
          )}
        </div>
      </div>
      {getStatusBadge()}
    </div>
  );
}
