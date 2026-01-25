import { cn } from '@/lib/utils';

interface ProgressProps {
  value: number;
  max?: number;
  variant?: 'default' | 'success' | 'warning' | 'error';
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  className?: string;
}

export function Progress({
  value,
  max = 100,
  variant = 'default',
  size = 'md',
  showLabel = false,
  className,
}: ProgressProps) {
  const percentage = Math.min(100, Math.max(0, (value / max) * 100));

  // Auto-determine variant based on percentage if not specified
  const autoVariant: 'default' | 'success' | 'warning' | 'error' =
    variant === 'default'
      ? percentage >= 80
        ? 'success'
        : percentage >= 50
        ? 'warning'
        : 'error'
      : variant;

  return (
    <div className={cn('w-full', className)}>
      {showLabel && (
        <div className="flex justify-between mb-1 text-sm">
          <span className="text-gray-600">{Math.round(percentage)}%</span>
        </div>
      )}
      <div
        className={cn(
          'w-full bg-gray-200 rounded-full overflow-hidden',
          size === 'sm' && 'h-1',
          size === 'md' && 'h-2',
          size === 'lg' && 'h-3'
        )}
      >
        <div
          className={cn(
            'h-full rounded-full transition-all duration-500',
            autoVariant === 'success' && 'bg-success',
            autoVariant === 'warning' && 'bg-warning',
            autoVariant === 'error' && 'bg-error'
          )}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}
