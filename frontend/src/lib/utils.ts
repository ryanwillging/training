import { clsx, type ClassValue } from 'clsx';

/**
 * Utility function for conditional class names
 */
export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

/**
 * Format a date string for display
 */
export function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  });
}

/**
 * Format a date as relative (Today, Tomorrow, etc.)
 */
export function formatRelativeDate(dateString: string): string {
  const date = new Date(dateString);
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const tomorrow = new Date(today);
  tomorrow.setDate(tomorrow.getDate() + 1);

  const targetDate = new Date(date);
  targetDate.setHours(0, 0, 0, 0);

  if (targetDate.getTime() === today.getTime()) {
    return 'Today';
  }
  if (targetDate.getTime() === tomorrow.getTime()) {
    return 'Tomorrow';
  }

  return formatDate(dateString);
}

/**
 * Format duration in minutes to human readable
 */
export function formatDuration(minutes: number | null): string {
  if (!minutes) return '';

  if (minutes < 60) {
    return `${minutes}min`;
  }

  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;

  if (mins === 0) {
    return `${hours}h`;
  }

  return `${hours}h ${mins}m`;
}

/**
 * Format time in seconds to mm:ss
 */
export function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Calculate percentage, capped at 100
 */
export function calculatePercentage(current: number, target: number): number {
  if (target === 0) return 0;
  return Math.min(100, Math.round((current / target) * 100));
}

/**
 * Get color class based on percentage
 */
export function getProgressColor(percentage: number): string {
  if (percentage >= 80) return 'text-success';
  if (percentage >= 50) return 'text-warning';
  return 'text-error';
}

/**
 * Workout type configuration
 */
export const WORKOUT_STYLES: Record<string, { icon: string; label: string; color: string }> = {
  swim_a: { icon: '🏊', label: 'Swim A', color: '#1976d2' },
  swim_b: { icon: '🏊', label: 'Swim B', color: '#1565c0' },
  swim_test: { icon: '🏊‍♂️', label: '400 TT Test', color: '#0d47a1' },
  lift_a: { icon: '🏋️', label: 'Lift A (Lower)', color: '#388e3c' },
  lift_b: { icon: '🏋️', label: 'Lift B (Upper)', color: '#2e7d32' },
  vo2: { icon: '🫀', label: 'VO2 Session', color: '#d32f2f' },
};

/**
 * Status colors
 */
export const STATUS_COLORS = {
  pending: { bg: '#fff3e0', text: '#e65100' },
  approved: { bg: '#e8f5e9', text: '#2e7d32' },
  rejected: { bg: '#ffebee', text: '#c62828' },
  completed: { bg: '#e8f5e9', text: '#2e7d32' },
  skipped: { bg: '#fff3e0', text: '#e65100' },
  synced: { bg: '#e3f2fd', text: '#1565c0' },
};

/**
 * Priority colors
 */
export const PRIORITY_COLORS = {
  high: { bg: '#ffebee', text: '#c62828' },
  medium: { bg: '#fff3e0', text: '#e65100' },
  low: { bg: '#e3f2fd', text: '#1565c0' },
};
