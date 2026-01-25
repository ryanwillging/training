import { cn } from '@/lib/utils';
import type { ReactNode } from 'react';

interface BadgeProps {
  children: ReactNode;
  variant?: 'default' | 'primary' | 'success' | 'warning' | 'error' | 'info';
  size?: 'sm' | 'md';
  className?: string;
  style?: React.CSSProperties;
}

export function Badge({
  children,
  variant = 'default',
  size = 'md',
  className,
  style,
}: BadgeProps) {
  return (
    <span
      style={style}
      className={cn(
        'inline-flex items-center font-medium rounded-lg',
        // Size
        size === 'sm' && 'px-2 py-0.5 text-xs',
        size === 'md' && 'px-3 py-1 text-xs',
        // Variants
        variant === 'default' && 'bg-gray-100 text-gray-600',
        variant === 'primary' && 'bg-primary/10 text-primary',
        variant === 'success' && 'bg-green-50 text-green-700',
        variant === 'warning' && 'bg-amber-50 text-amber-700',
        variant === 'error' && 'bg-red-50 text-red-700',
        variant === 'info' && 'bg-blue-50 text-blue-700',
        className
      )}
    >
      {children}
    </span>
  );
}

interface StatusBadgeProps {
  status: 'pending' | 'approved' | 'rejected' | 'completed' | 'skipped' | 'synced';
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const config: Record<string, { label: string; variant: BadgeProps['variant'] }> = {
    pending: { label: 'Pending', variant: 'warning' },
    approved: { label: 'Approved', variant: 'success' },
    rejected: { label: 'Rejected', variant: 'error' },
    completed: { label: 'Completed', variant: 'success' },
    skipped: { label: 'Skipped', variant: 'warning' },
    synced: { label: 'Synced', variant: 'info' },
  };

  const { label, variant } = config[status] || { label: status, variant: 'default' };

  return (
    <Badge variant={variant} className={className}>
      {label}
    </Badge>
  );
}
