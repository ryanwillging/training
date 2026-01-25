'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  Badge,
  LoadingState,
} from '@/components/ui';
import { LineChart, BarChart } from '@/components/charts';
import { wellnessApi, planApi } from '@/lib/api';
import { Calendar, TrendingUp, Moon, Heart, Battery, Activity } from 'lucide-react';

type TimeRange = '7' | '30' | '90' | 'all';

export default function ExplorePage() {
  const [timeRange, setTimeRange] = useState<TimeRange>('30');

  const days = timeRange === 'all' ? 365 : parseInt(timeRange);

  const { data: wellnessData, isLoading } = useQuery({
    queryKey: ['wellness-history', days],
    queryFn: () => wellnessApi.getHistory(days),
  });

  const { data: planStatus } = useQuery({
    queryKey: ['plan-status'],
    queryFn: planApi.getStatus,
  });

  if (isLoading) {
    return <LoadingState message="Loading wellness data..." />;
  }

  const data = wellnessData || [];

  // Prepare chart data (reverse to show oldest first)
  const chartData = [...data].reverse().map((d) => ({
    date: new Date(d.date).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    }),
    hrv: d.hrv,
    rhr: d.resting_heart_rate,
    bodyBattery: d.body_battery,
    sleepScore: d.sleep_score,
    sleepHours: d.sleep_duration_hours,
    stress: d.stress_level,
    steps: d.steps,
  }));

  // Calculate averages
  const calculateAvg = (key: keyof typeof chartData[0]) => {
    const values = chartData
      .map((d) => d[key])
      .filter((v) => v !== null && v !== undefined) as number[];
    if (values.length === 0) return null;
    return Math.round((values.reduce((a, b) => a + b, 0) / values.length) * 10) / 10;
  };

  const avgHrv = calculateAvg('hrv');
  const avgRhr = calculateAvg('rhr');
  const avgBodyBattery = calculateAvg('bodyBattery');
  const avgSleepScore = calculateAvg('sleepScore');
  const avgSleepHours = calculateAvg('sleepHours');
  const avgStress = calculateAvg('stress');
  const avgSteps = calculateAvg('steps');

  // Calculate trends (compare first half to second half)
  const calculateTrend = (key: keyof typeof chartData[0]) => {
    const values = chartData
      .map((d) => d[key])
      .filter((v) => v !== null && v !== undefined) as number[];
    if (values.length < 4) return null;

    const mid = Math.floor(values.length / 2);
    const firstHalf = values.slice(0, mid);
    const secondHalf = values.slice(mid);

    const avgFirst = firstHalf.reduce((a, b) => a + b, 0) / firstHalf.length;
    const avgSecond = secondHalf.reduce((a, b) => a + b, 0) / secondHalf.length;

    const change = ((avgSecond - avgFirst) / avgFirst) * 100;
    return Math.round(change * 10) / 10;
  };

  const hrvTrend = calculateTrend('hrv');
  const rhrTrend = calculateTrend('rhr');
  const sleepTrend = calculateTrend('sleepScore');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-medium text-gray-900">Explore</h1>
          <p className="text-gray-500 mt-1">
            Long-term trends and wellness insights
          </p>
        </div>

        {/* Time Range Selector */}
        <div className="flex items-center gap-2 bg-gray-100 p-1 rounded-full">
          {(['7', '30', '90', 'all'] as TimeRange[]).map((range) => (
            <button
              key={range}
              onClick={() => setTimeRange(range)}
              className={`px-4 py-1.5 text-sm font-medium rounded-full transition-colors ${
                timeRange === range
                  ? 'bg-white text-primary shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              {range === 'all' ? 'All' : `${range}d`}
            </button>
          ))}
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          icon={<Heart className="w-5 h-5 text-red-500" />}
          label="Avg HRV"
          value={avgHrv !== null ? `${avgHrv}ms` : '--'}
          trend={hrvTrend}
          trendLabel="vs previous period"
          trendInverse={false}
        />
        <StatCard
          icon={<Activity className="w-5 h-5 text-blue-500" />}
          label="Avg RHR"
          value={avgRhr !== null ? `${avgRhr}bpm` : '--'}
          trend={rhrTrend}
          trendLabel="vs previous period"
          trendInverse={true}
        />
        <StatCard
          icon={<Moon className="w-5 h-5 text-purple-500" />}
          label="Avg Sleep Score"
          value={avgSleepScore !== null ? `${avgSleepScore}` : '--'}
          trend={sleepTrend}
          trendLabel="vs previous period"
          trendInverse={false}
        />
        <StatCard
          icon={<Battery className="w-5 h-5 text-green-500" />}
          label="Avg Body Battery"
          value={avgBodyBattery !== null ? `${avgBodyBattery}%` : '--'}
        />
      </div>

      {/* HRV Trend */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-primary" />
            HRV Trend
          </CardTitle>
        </CardHeader>
        <CardContent>
          {chartData.length > 0 ? (
            <LineChart
              data={chartData.filter((d) => d.hrv !== null)}
              xKey="date"
              yKey="hrv"
              color="#d32f2f"
              height={250}
            />
          ) : (
            <EmptyChart />
          )}
        </CardContent>
      </Card>

      {/* Sleep Score & Duration */}
      <div className="grid md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Moon className="w-5 h-5 text-purple-500" />
              Sleep Score Trend
            </CardTitle>
          </CardHeader>
          <CardContent>
            {chartData.length > 0 ? (
              <LineChart
                data={chartData.filter((d) => d.sleepScore !== null)}
                xKey="date"
                yKey="sleepScore"
                color="#7c3aed"
                height={200}
              />
            ) : (
              <EmptyChart />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Moon className="w-5 h-5 text-indigo-500" />
              Sleep Duration
            </CardTitle>
          </CardHeader>
          <CardContent>
            {chartData.length > 0 ? (
              <BarChart
                data={chartData.filter((d) => d.sleepHours !== null)}
                xKey="date"
                yKey="sleepHours"
                color="#6366f1"
                height={200}
              />
            ) : (
              <EmptyChart />
            )}
          </CardContent>
        </Card>
      </div>

      {/* Body Battery & Stress */}
      <div className="grid md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Battery className="w-5 h-5 text-green-500" />
              Body Battery Pattern
            </CardTitle>
          </CardHeader>
          <CardContent>
            {chartData.length > 0 ? (
              <LineChart
                data={chartData.filter((d) => d.bodyBattery !== null)}
                xKey="date"
                yKey="bodyBattery"
                color="#22c55e"
                height={200}
              />
            ) : (
              <EmptyChart />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="w-5 h-5 text-orange-500" />
              Stress Levels
            </CardTitle>
          </CardHeader>
          <CardContent>
            {chartData.length > 0 ? (
              <LineChart
                data={chartData.filter((d) => d.stress !== null)}
                xKey="date"
                yKey="stress"
                color="#f97316"
                height={200}
              />
            ) : (
              <EmptyChart />
            )}
          </CardContent>
        </Card>
      </div>

      {/* Resting Heart Rate */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Heart className="w-5 h-5 text-red-500" />
            Resting Heart Rate
          </CardTitle>
        </CardHeader>
        <CardContent>
          {chartData.length > 0 ? (
            <LineChart
              data={chartData.filter((d) => d.rhr !== null)}
              xKey="date"
              yKey="rhr"
              color="#ef4444"
              height={200}
            />
          ) : (
            <EmptyChart />
          )}
        </CardContent>
      </Card>

      {/* Daily Steps */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="w-5 h-5 text-blue-500" />
            Daily Steps
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="mb-4 text-sm text-gray-600">
            Average: {avgSteps !== null ? Math.round(avgSteps).toLocaleString() : '--'} steps/day
          </div>
          {chartData.length > 0 ? (
            <BarChart
              data={chartData.filter((d) => d.steps !== null)}
              xKey="date"
              yKey="steps"
              color="#3b82f6"
              height={200}
            />
          ) : (
            <EmptyChart />
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
  trend,
  trendLabel,
  trendInverse = false,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  trend?: number | null;
  trendLabel?: string;
  trendInverse?: boolean;
}) {
  const getTrendColor = () => {
    if (trend === null || trend === undefined) return '';
    const isPositive = trendInverse ? trend < 0 : trend > 0;
    return isPositive ? 'text-green-600' : 'text-red-600';
  };

  const getTrendIcon = () => {
    if (trend === null || trend === undefined) return '';
    return trend > 0 ? '↑' : trend < 0 ? '↓' : '→';
  };

  return (
    <Card>
      <CardContent className="py-4">
        <div className="flex items-center gap-2 text-gray-500 mb-2">
          {icon}
          <span className="text-sm">{label}</span>
        </div>
        <p className="text-2xl font-semibold text-gray-900">{value}</p>
        {trend !== null && trend !== undefined && (
          <p className={`text-sm mt-1 ${getTrendColor()}`}>
            {getTrendIcon()} {Math.abs(trend)}% {trendLabel}
          </p>
        )}
      </CardContent>
    </Card>
  );
}

function EmptyChart() {
  return (
    <div className="flex items-center justify-center h-[200px] bg-gray-50 rounded-lg">
      <p className="text-sm text-gray-500">No data available</p>
    </div>
  );
}
