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
import { Target, TrendingUp, Calendar, Plus, Check } from 'lucide-react';

// Performance test types
const TEST_TYPES = [
  { value: 'swim_400_tt', label: '400yd Freestyle TT', unit: 'seconds' },
  { value: 'vertical_jump', label: 'Vertical Jump', unit: 'inches' },
  { value: 'broad_jump', label: 'Broad Jump', unit: 'inches' },
  { value: 'flexibility', label: 'Sit and Reach', unit: 'inches' },
  { value: 'body_fat', label: 'Body Fat %', unit: '%' },
  { value: 'weight', label: 'Weight', unit: 'lbs' },
];

export default function GoalsPage() {
  const [showTestForm, setShowTestForm] = useState(false);
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
      setShowTestForm(false);
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
          <h1 className="text-2xl sm:text-3xl font-medium text-gray-900">Goals</h1>
          <p className="text-gray-500 mt-1">
            Week {currentWeek} of 24
            {isTestWeek && (
              <Badge variant="warning" className="ml-2">
                Test Week
              </Badge>
            )}
          </p>
        </div>
        <Button onClick={() => setShowTestForm(true)}>
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

      {/* Log Test Form Modal */}
      {showTestForm && (
        <Card className="border-2 border-primary">
          <CardHeader>
            <CardTitle>Log Performance Test</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
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
                  onClick={handleSubmitTest}
                  disabled={!testValue || logTestMutation.isPending}
                >
                  {logTestMutation.isPending ? 'Saving...' : 'Save Result'}
                </Button>
                <Button variant="outlined" onClick={() => setShowTestForm(false)}>
                  Cancel
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Active Goals */}
      <div>
        <h2 className="text-lg font-medium text-gray-900 mb-4 flex items-center gap-2">
          <Target className="w-5 h-5 text-primary" />
          Active Goals
        </h2>
        <div className="grid gap-4">
          {goals.map((goal) => (
            <Card key={goal.id}>
              <CardContent className="py-4">
                <div className="flex flex-col sm:flex-row sm:items-center gap-4">
                  <div className="flex-1">
                    <h3 className="font-medium text-gray-900">{goal.name}</h3>
                    <div className="flex items-center gap-4 mt-2 text-sm text-gray-500">
                      <span>Target: {goal.target}</span>
                      <span>Current: {goal.current}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <p className="text-2xl font-semibold">
                        {goal.progress > 0 ? `${goal.progress}%` : '--'}
                      </p>
                      <p className="text-xs text-gray-500">{goal.deadline}</p>
                    </div>
                  </div>
                </div>
                {goal.progress > 0 && (
                  <div className="mt-3">
                    <Progress value={goal.progress} />
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {/* Body Composition Charts */}
      <div className="grid md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-primary" />
              Body Fat Trend
            </CardTitle>
          </CardHeader>
          <CardContent>
            {bodyFatChartData.length > 0 ? (
              <LineChart
                data={bodyFatChartData}
                xKey="date"
                yKey="value"
                color="#1976d2"
                height={200}
              />
            ) : (
              <div className="text-center py-8 text-gray-500">
                <p>No body fat data recorded yet</p>
                <p className="text-sm mt-1">Log your first measurement to see trends</p>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-primary" />
              Weight Trend
            </CardTitle>
          </CardHeader>
          <CardContent>
            {weightChartData.length > 0 ? (
              <LineChart
                data={weightChartData}
                xKey="date"
                yKey="value"
                color="#2e7d32"
                height={200}
              />
            ) : (
              <div className="text-center py-8 text-gray-500">
                <p>No weight data recorded yet</p>
                <p className="text-sm mt-1">Log your first measurement to see trends</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Test Schedule */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Calendar className="w-5 h-5 text-primary" />
            Test Schedule
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[
              { week: 2, label: 'Baseline Testing', status: currentWeek > 2 ? 'complete' : currentWeek === 2 ? 'current' : 'upcoming' },
              { week: 12, label: 'Mid-Program Testing', status: currentWeek > 12 ? 'complete' : currentWeek === 12 ? 'current' : 'upcoming' },
              { week: 24, label: 'Final Testing', status: currentWeek > 24 ? 'complete' : currentWeek === 24 ? 'current' : 'upcoming' },
            ].map((test) => (
              <div
                key={test.week}
                className={`flex items-center gap-3 p-3 rounded-lg ${
                  test.status === 'current'
                    ? 'bg-amber-50 border border-amber-200'
                    : test.status === 'complete'
                    ? 'bg-green-50'
                    : 'bg-gray-50'
                }`}
              >
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center ${
                    test.status === 'complete'
                      ? 'bg-green-500 text-white'
                      : test.status === 'current'
                      ? 'bg-amber-500 text-white'
                      : 'bg-gray-300'
                  }`}
                >
                  {test.status === 'complete' ? (
                    <Check className="w-5 h-5" />
                  ) : (
                    <span className="text-sm font-medium">{test.week}</span>
                  )}
                </div>
                <div className="flex-1">
                  <p className="font-medium text-gray-900">{test.label}</p>
                  <p className="text-sm text-gray-500">Week {test.week}</p>
                </div>
                <Badge
                  variant={
                    test.status === 'complete'
                      ? 'success'
                      : test.status === 'current'
                      ? 'warning'
                      : 'default'
                  }
                >
                  {test.status === 'complete'
                    ? 'Complete'
                    : test.status === 'current'
                    ? 'This Week'
                    : 'Upcoming'}
                </Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
