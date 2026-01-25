'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Card,
  CardContent,
  Badge,
  LoadingState,
} from '@/components/ui';
import { planApi, type ScheduledWorkout } from '@/lib/api';
import { WORKOUT_STYLES, formatDuration, formatRelativeDate } from '@/lib/utils';
import { Calendar, ChevronRight } from 'lucide-react';

export default function UpcomingPage() {
  const [daysAhead, setDaysAhead] = useState(14);

  const { data, isLoading } = useQuery({
    queryKey: ['upcoming', daysAhead],
    queryFn: () => planApi.getUpcoming(daysAhead),
  });

  if (isLoading) {
    return <LoadingState message="Loading upcoming workouts..." />;
  }

  const workouts = data?.workouts || [];

  // Group workouts by date
  const workoutsByDate = workouts.reduce((acc, workout) => {
    const date = workout.scheduled_date;
    if (!acc[date]) {
      acc[date] = [];
    }
    acc[date].push(workout);
    return acc;
  }, {} as Record<string, ScheduledWorkout[]>);

  const sortedDates = Object.keys(workoutsByDate).sort();
  const today = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/New_York',
  }).format(new Date());

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="md-headline-large text-2xl sm:text-3xl font-medium text-gray-900">
            Upcoming Workouts
          </h1>
          <p className="text-gray-500 mt-1">
            Next {daysAhead} days · {sortedDates.length} training days
          </p>
        </div>

        {/* Days Selector */}
        <div className="flex items-center gap-2 bg-gray-100 p-1 rounded-full">
          {[7, 14, 30].map((days) => (
            <button
              key={days}
              onClick={() => setDaysAhead(days)}
              className={`px-4 py-1.5 text-sm font-medium rounded-full transition-colors ${
                daysAhead === days
                  ? 'bg-white text-primary shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              {days}d
            </button>
          ))}
        </div>
      </div>

      {/* Workouts List */}
      {sortedDates.length === 0 ? (
        <Card>
          <CardContent className="text-center py-12">
            <Calendar className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              No Upcoming Workouts
            </h3>
            <p className="text-sm text-gray-500">
              Initialize your training plan to see scheduled workouts.
            </p>
            <ul className="sr-only">
              <li>No scheduled workouts</li>
            </ul>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {sortedDates.map((date) => {
            const dayWorkouts = workoutsByDate[date];
            const isToday = date === today;
            const dateObj = new Date(date + 'T00:00:00');

            return (
              <Card
                key={date}
                className={isToday ? 'ring-2 ring-primary ring-offset-2' : ''}
              >
                {/* Day Header */}
                <div
                  className={`flex items-center gap-4 px-4 py-3 border-b border-gray-100 ${
                    isToday ? 'bg-primary/5' : 'bg-gray-50'
                  }`}
                >
                  <div className="text-center min-w-[48px]">
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                      {dateObj.toLocaleDateString('en-US', { weekday: 'short' })}
                    </p>
                    <p
                      className={`text-2xl font-semibold ${
                        isToday ? 'text-primary' : 'text-gray-900'
                      }`}
                    >
                      {dateObj.getDate()}
                    </p>
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">
                      {formatRelativeDate(date)}
                    </p>
                    <p className="text-sm text-gray-500">
                      {dateObj.toLocaleDateString('en-US', {
                        month: 'long',
                        year: 'numeric',
                      })}
                    </p>
                  </div>
                  {isToday && (
                    <Badge variant="primary" className="ml-auto">
                      Today
                    </Badge>
                  )}
                </div>

                {/* Workouts */}
                <CardContent className="p-0">
                  <div className="divide-y divide-gray-100">
                    {dayWorkouts.map((workout) => (
                      <WorkoutRow key={workout.id} workout={workout} />
                    ))}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}

function WorkoutRow({ workout }: { workout: ScheduledWorkout }) {
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
      className="flex items-center gap-3 p-4 hover:bg-gray-50 transition-colors"
      style={{ borderLeft: `4px solid ${style.color}` }}
    >
      {/* Icon */}
      <div
        className="w-10 h-10 rounded-full flex items-center justify-center text-xl flex-shrink-0"
        style={{ backgroundColor: `${style.color}20` }}
      >
        {style.icon}
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <p className="font-medium text-gray-900 truncate">
          {workout.workout_name || style.label}
        </p>
        <div className="flex items-center gap-2 flex-wrap mt-1">
          <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full">
            Week {workout.week_number}
          </span>
          {workout.duration_minutes && (
            <span className="text-xs text-gray-500">
              {formatDuration(workout.duration_minutes)}
            </span>
          )}
          {workout.is_test_week && (
            <Badge variant="warning" size="sm">
              TEST WEEK
            </Badge>
          )}
        </div>
      </div>

      {/* Status */}
      <div className="flex-shrink-0">{getStatusBadge()}</div>
    </div>
  );
}
