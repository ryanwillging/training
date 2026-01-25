'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  Button,
  Badge,
  Progress,
  LoadingState,
} from '@/components/ui';
import { LineChart } from '@/components/charts';
import { metricsApi, planApi } from '@/lib/api';
import { TrendingUp, Plus } from 'lucide-react';

// Performance test types
const TEST_TYPES = [
  { value: 'swim_400_tt', label: '400yd Freestyle TT', unit: 'seconds' },
  { value: 'vertical_jump', label: 'Vertical Jump', unit: 'inches' },
  { value: 'broad_jump', label: 'Broad Jump', unit: 'inches' },
  { value: 'flexibility', label: 'Sit and Reach', unit: 'inches' },
  { value: 'body_fat', label: 'Body Fat %', unit: '%' },
  { value: 'weight', label: 'Weight', unit: 'lbs' },
];

export function GoalsPage() {
  const [testType, setTestType] = useState(TEST_TYPES[0].value);
  const [testValue, setTestValue] = useState('');
  const [testNotes, setTestNotes] = useState('');
  const queryClient = useQueryClient();

  const { data: planStatus, isLoading: statusLoading } = useQuery({
    queryKey: ['plan-status'],
    queryFn: planApi.getStatus,
  });

  const { data: weekSummary } = useQuery({
    queryKey: ['week-summary'],
    queryFn: () => planApi.getWeekSummary(),
  });

  // Fetch metric history for body composition
  const { data: bodyFatHistory } = useQuery({
    queryKey: ['metrics-history', 'body_fat'],
    queryFn: () => metricsApi.getHistory('body_fat', 1, 30),
  });

  const { data: weightHistory } = useQuery({
    queryKey: ['metrics-history', 'weight'],
    queryFn: () => metricsApi.getHistory('weight', 1, 30),
  });

  // Log performance test mutation
  const logTestMutation = useMutation({
    mutationFn: (data: {
      athlete_id: number;
      metric_type: string;
      value: number;
      unit: string;
      test_date: string;
      notes?: string;
    }) => metricsApi.logPerformanceTest(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['metrics-history'] });
      setTestValue('');
      setTestNotes('');
    },
  });

  const handleSubmitTest = () => {
    const selectedTest = TEST_TYPES.find((t) => t.value === testType);
    if (!selectedTest || !testValue) return;

    logTestMutation.mutate({
      athlete_id: 1,
      metric_type: testType,
      value: parseFloat(testValue),
      unit: selectedTest.unit,
      test_date: new Date().toISOString().split('T')[0],
      notes: testNotes || undefined,
    });
  };

  if (statusLoading) {
    return <LoadingState message="Loading goals..." />;
  }

  const isTestWeek = weekSummary?.is_test_week || false;
  const currentWeek = planStatus?.current_week || 1;

  // Calculate goal progress (placeholder targets)
  const goals = [
    {
      id: 1,
      name: 'Primary: 400yd Freestyle',
      target: 'TBD after baseline',
      current: 'Baseline pending',
      progress: 0,
      deadline: 'Week 24',
    },
    {
      id: 2,
      name: 'Body Composition',
      target: '12% body fat',
      current: bodyFatHistory?.data && bodyFatHistory.data.length > 0
        ? `${bodyFatHistory.data[0].value}%`
        : 'No data',
      progress: 40,
      deadline: 'Week 24',
    },
    {
      id: 3,
      name: 'Weekly Adherence',
      target: '80%+ completion',
      current: weekSummary?.completion_rate
        ? `${Math.round(weekSummary.completion_rate)}%`
        : '0%',
      progress: weekSummary?.completion_rate || 0,
      deadline: 'Ongoing',
    },
  ];

  // Prepare chart data
  const bodyFatChartData =
    bodyFatHistory?.data?.map((d) => ({
      date: new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      value: d.value,
    })).reverse() || [];

  const weightChartData =
    weightHistory?.data?.map((d) => ({
      date: new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      value: d.value,
    })).reverse() || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="md-headline-large text-2xl sm:text-3xl font-medium text-gray-900">
            Goals
          </h1>
          <p className="text-gray-500 mt-1">
            Week {currentWeek} of 24
            {isTestWeek && (
              <Badge variant="warning" className="ml-2">
                Test Week
              </Badge>
            )}
          </p>
        </div>
        <Button
          type="button"
          onClick={() => {
            const target = document.getElementById('performance-test-form');
            target?.scrollIntoView({ behavior: 'smooth', block: 'start' });
          }}
        >
          <Plus className="w-4 h-4" />
          Log Test Result
        </Button>
      </div>

      {/* Test Week Alert */}
      {isTestWeek && (
        <Card className="bg-amber-50 border-amber-200">
          <CardContent className="py-4">
            <div className="flex items-start gap-3">
              <div className="text-2xl">🎯</div>
              <div>
                <h3 className="font-medium text-amber-800">Test Week</h3>
                <p className="text-sm text-amber-700 mt-1">
                  This is a scheduled performance testing week. Log your test results
                  to track progress toward your goals.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Goals Overview */}
      <div className="grid md:grid-cols-3 gap-4">
        {goals.map((goal) => (
          <Card key={goal.id}>
            <CardHeader>
              <CardTitle>{goal.name}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div>
                  <p className="text-xs text-gray-500 mb-1">Current</p>
                  <p className="text-lg font-medium">{goal.current}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 mb-1">Target</p>
                  <p className="text-sm text-gray-700">{goal.target}</p>
                </div>
                <div>
                  <Progress value={goal.progress} />
                  <p className="text-xs text-gray-500 mt-1">Deadline: {goal.deadline}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Metrics Charts */}
      <div className="grid md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-primary" />
              Body Fat %
            </CardTitle>
          </CardHeader>
          <CardContent>
            {bodyFatChartData.length > 0 ? (
              <LineChart
                data={bodyFatChartData}
                xKey="date"
                yKey="value"
                color="#d32f2f"
                height={200}
              />
            ) : (
              <p className="text-sm text-gray-500">No data yet</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-primary" />
              Weight (lbs)
            </CardTitle>
          </CardHeader>
          <CardContent>
            {weightChartData.length > 0 ? (
              <LineChart
                data={weightChartData}
                xKey="date"
                yKey="value"
                color="#1976d2"
                height={200}
              />
            ) : (
              <p className="text-sm text-gray-500">No data yet</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Log Test Form */}
      <div id="performance-test-form">
      <Card className="border-2 border-primary">
        <CardHeader>
          <CardTitle>Log Performance Test</CardTitle>
        </CardHeader>
        <CardContent>
          <form
            onSubmit={(event) => {
              event.preventDefault();
              handleSubmitTest();
            }}
            className="space-y-4"
          >
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Test Type
              </label>
              <select
                value={testType}
                onChange={(e) => setTestType(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              >
                {TEST_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Value ({TEST_TYPES.find((t) => t.value === testType)?.unit})
              </label>
              <input
                type="number"
                value={testValue}
                onChange={(e) => setTestValue(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="Enter value"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Notes (optional)
              </label>
              <textarea
                value={testNotes}
                onChange={(e) => setTestNotes(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                rows={2}
                placeholder="Any additional notes..."
              />
            </div>
            <div className="flex gap-2">
              <Button
                type="submit"
                disabled={!testValue || logTestMutation.isPending}
              >
                {logTestMutation.isPending ? 'Saving...' : 'Save Result'}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
      </div>
    </div>
  );
}
