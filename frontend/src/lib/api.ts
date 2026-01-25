/**
 * API client for communicating with the FastAPI backend.
 */

const API_BASE = '/api';

export interface ApiError {
  detail: string;
  status: number;
}

async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;

  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw {
      detail: error.detail || response.statusText,
      status: response.status,
    } as ApiError;
  }

  return response.json();
}

// Plan endpoints
export interface PlanStatus {
  initialized: boolean;
  current_week: number;
  total_weeks: number;
  start_date: string | null;
  end_date: string | null;
  is_test_week: boolean;
  next_test_week: number | null;
  days_until_end: number | null;
}

export interface ScheduledWorkout {
  id: number;
  workout_type: string;
  workout_name: string;
  scheduled_date: string;
  week_number: number;
  status: string;
  duration_minutes: number | null;
  is_test_week: boolean;
  garmin_workout_id: string | null;
}

export interface UpcomingWorkouts {
  days_ahead: number;
  workouts: ScheduledWorkout[];
}

export interface WeekSummary {
  week_number: number;
  start_date: string;
  end_date: string;
  workouts: ScheduledWorkout[];
  completion_rate: number;
  is_test_week: boolean;
}

export interface DailyReview {
  id: number;
  date: string;
  approval_status: string;
  progress_summary: Record<string, unknown> | null;
  insights: string;
  recommendations: string;
  proposed_adjustments: Modification[];
  created_at: string | null;
}

export interface Modification {
  type: string;
  description: string;
  reason: string;
  priority: 'high' | 'medium' | 'low';
  week: number;
  status: 'pending' | 'approved' | 'rejected';
  actioned_at?: string;
}

export const planApi = {
  getStatus: () => fetchApi<PlanStatus>('/plan/status'),

  getUpcoming: (days: number = 7) =>
    fetchApi<UpcomingWorkouts>(`/plan/upcoming?days=${days}`),

  getWeekSummary: (weekNumber?: number) =>
    fetchApi<WeekSummary>(weekNumber ? `/plan/week/${weekNumber}` : '/plan/week'),

  getLatestReview: () => fetchApi<DailyReview>('/plan/reviews/latest'),

  actionModification: (reviewId: number, modIndex: number, action: 'approve' | 'reject') =>
    fetchApi(`/plan/reviews/${reviewId}/modifications/${modIndex}/action`, {
      method: 'POST',
      body: JSON.stringify({ action }),
    }),

  actionReview: (reviewId: number, action: 'approve' | 'reject', notes?: string) =>
    fetchApi(`/plan/reviews/${reviewId}/action`, {
      method: 'POST',
      body: JSON.stringify({ action, notes }),
    }),

  runEvaluation: (userContext?: string) =>
    fetchApi('/plan/evaluate-with-context', {
      method: 'POST',
      body: JSON.stringify({ user_context: userContext }),
    }),

  getEvaluationContext: () => fetchApi('/plan/evaluation-context'),
};

// Wellness endpoints
export interface WellnessData {
  date: string;
  hrv: number | null;
  resting_heart_rate: number | null;
  body_battery: number | null;
  sleep_score: number | null;
  sleep_duration_hours: number | null;
  rem_sleep_minutes: number | null;
  deep_sleep_minutes: number | null;
  light_sleep_minutes: number | null;
  awake_minutes: number | null;
  stress_level: number | null;
  steps: number | null;
  active_calories: number | null;
}

export const wellnessApi = {
  getLatest: () => fetchApi<WellnessData>('/wellness/latest'),

  getHistory: (days: number = 30) =>
    fetchApi<WellnessData[]>(`/wellness?days=${days}`),
};

// Metrics/Goals endpoints
export interface Goal {
  id: number;
  name: string;
  metric_type: string;
  target_value: number;
  current_value: number;
  unit: string;
  deadline: string | null;
  progress_pct: number;
}

export interface PerformanceTest {
  id: number;
  metric_type: string;
  value: number;
  unit: string;
  test_date: string;
  notes: string | null;
}

export interface MetricsHistoryResponse {
  metric_type: string;
  athlete_id: number;
  count: number;
  data: Array<{
    id: number;
    date: string;
    value: number;
    value_text: string | null;
    notes: string | null;
    data?: Record<string, unknown>;
  }>;
}

export const metricsApi = {
  getHistory: (metricType: string, athleteId: number = 1, limit: number = 30) =>
    fetchApi<MetricsHistoryResponse>(`/metrics/history/${metricType}?athlete_id=${athleteId}&limit=${limit}`),

  logPerformanceTest: (data: {
    athlete_id: number;
    metric_type: string;
    value: number;
    unit: string;
    test_date: string;
    notes?: string;
  }) =>
    fetchApi('/metrics/performance-test', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  logBodyComposition: (data: {
    athlete_id: number;
    measurement_date: string;
    body_fat_pct?: number;
    weight_lbs?: number;
    measurement_method?: string;
    notes?: string;
  }) =>
    fetchApi('/metrics/body-composition', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
};

// Sync status endpoint
export interface SyncStatus {
  last_sync: string | null;
  job_type: string | null;
  status: string;
  hours_since_sync: number | null;
  message: string;
}

export const syncApi = {
  getStatus: () => fetchApi<SyncStatus>('/cron/sync/status'),

  triggerSync: () => fetchApi('/cron/sync/trigger', {
    method: 'POST',
  }),
};

// Reports endpoints (for explore dashboard)
export const reportsApi = {
  getDaily: () => fetchApi('/reports/daily'),
  getWeekly: () => fetchApi('/reports/weekly'),
};
