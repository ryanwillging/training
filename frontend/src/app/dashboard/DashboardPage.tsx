'use client';

import {
  TodaysPlanWidget,
  RecoveryWidget,
  GoalsRingsWidget,
  ThisWeekWidget,
  PlanChangesWidget,
  SleepWidget,
  SyncStatusWidget,
} from '@/components/dashboard';

export function DashboardPage() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <header className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="md-headline-large text-2xl sm:text-3xl font-medium text-gray-900">
            Dashboard
          </h1>
          <p className="text-gray-500 mt-1">
            {new Date().toLocaleDateString('en-US', {
              weekday: 'long',
              month: 'long',
              day: 'numeric',
              timeZone: 'America/New_York',
            })}
          </p>
        </div>
        <SyncStatusWidget />
      </header>

      {/* Dashboard Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 lg:gap-6">
        {/* Row 1 */}
        <div className="md:col-span-1">
          <TodaysPlanWidget />
        </div>
        <div className="md:col-span-1">
          <RecoveryWidget />
        </div>
        <div className="md:col-span-1">
          <GoalsRingsWidget />
        </div>

        {/* Row 2 */}
        <div className="md:col-span-1">
          <ThisWeekWidget />
        </div>
        <div className="md:col-span-1">
          <PlanChangesWidget />
        </div>
        <div className="md:col-span-1">
          <SleepWidget />
        </div>
      </div>
    </div>
  );
}
