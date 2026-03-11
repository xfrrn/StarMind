import React from 'react';
import { cn } from '../utils';

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'outline' | 'secondary' | 'accent' | 'success';
}

export function Badge({ className, variant = 'default', children, ...props }: BadgeProps) {
  const variants = {
    default: "bg-zinc-100 text-zinc-900 dark:bg-zinc-800 dark:text-zinc-100",
    outline: "border border-zinc-200 text-zinc-600 dark:border-zinc-800 dark:text-zinc-400",
    secondary: "bg-zinc-100/50 text-zinc-600 dark:bg-zinc-900 dark:text-zinc-400",
    accent: "bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
    success: "bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300",
  };

  return (
    <span 
      className={cn(
        "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium",
        variants[variant],
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
}
