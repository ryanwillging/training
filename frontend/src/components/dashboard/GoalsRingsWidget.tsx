'use client';

import { useQuery } from '@tanstack/react-query';
import { Card, CardHeader, CardTitle, CardContent, LoadingState } from '@/components/ui';
import { ActivityRings } from '@/components/charts';
import { planApi } from '@/lib/api';

// Goal ring colors (similar to Apple's Activity rings)
const RING_COLORS = {
  swim: '#1976d2', // Blue - Swim goal
  strength: '#2e7d32', // Green - Strength goal
  fitness: '#d32f2f', // Red - VO2/Fitness goal
};

export function GoalsRingsWidget() {
  const { data: weekData, isLoading } = useQuery({
    queryKey: ['week-summary'],
    queryFn: () => planApi.getWeekSummary(),
  });

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Goals Progress</CardTitle>
        </CardHeader>
        <CardContent>
          <LoadingState message="Loading goals..." />
        </CardContent>
      </Card>
    );
  }

  // Calculate progress for each goal category
  const workouts = weekData?.workouts || [];

  const swimWorkouts = workouts.filter(
    (w) => w.workout_type && w.workout_type.startsWith('swim')
  );
  const liftWorkouts = workouts.filter(
    (w) => w.workout_type && w.workout_type.startsWith('lift')
  );
  const vo2Workouts = workouts.filter(
    (w) => w.workout_type === 'vo2'
  );

  const swimCompleted = swimWorkouts.filter((w) => w.status === 'completed').length;
  const liftCompleted = liftWorkouts.filter((w) => w.status === 'completed').length;
  const vo2Completed = vo2Workouts.filter((w) => w.status === 'completed').length;

  // Weekly targets
  const swimTarget = 2; // 2 swim sessions per week
  const liftTarget = 2; // 2 lift sessions per week
  const vo2Target = 1; // 1 VO2 session per week

  const rings = [
    {
      value: swimCompleted,
      max: swimTarget,
      color: RING_COLORS.swim,
      label: `Swim (${swimCompleted}/${swimTarget})`,
    },
    {
      value: liftCompleted,
      max: liftTarget,
      color: RING_COLORS.strength,
      label: `Strength (${liftCompleted}/${liftTarget})`,
    },
    {
      value: vo2Completed,
      max: vo2Target,
      color: RING_COLORS.fitness,
      label: `VO2 (${vo2Completed}/${vo2Target})`,
    },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Goals Progress</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex justify-center">
          <ActivityRings rings={rings} size={180} strokeWidth={14} />
        </div>
      </CardContent>
    </Card>
  );
}
