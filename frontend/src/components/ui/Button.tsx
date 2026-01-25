import { cn } from '@/lib/utils';
import type { ButtonHTMLAttributes, ReactNode } from 'react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  variant?: 'filled' | 'outlined' | 'text';
  size?: 'sm' | 'md' | 'lg';
  fullWidth?: boolean;
}

export function Button({
  children,
  className,
  variant = 'filled',
  size = 'md',
  fullWidth = false,
  disabled,
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn(
        'inline-flex items-center justify-center gap-2 font-medium rounded-full transition-all',
        'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        // Size variants
        size === 'sm' && 'px-4 py-1.5 text-sm',
        size === 'md' && 'px-6 py-2 text-sm',
        size === 'lg' && 'px-8 py-3 text-base',
        // Style variants
        variant === 'filled' &&
          'bg-primary text-white hover:bg-primary-dark hover:shadow-md-1',
        variant === 'outlined' &&
          'bg-transparent text-primary border border-outline hover:bg-primary/5',
        variant === 'text' && 'bg-transparent text-primary hover:bg-primary/5',
        // Full width
        fullWidth && 'w-full',
        className
      )}
      disabled={disabled}
      {...props}
    >
      {children}
    </button>
  );
}
