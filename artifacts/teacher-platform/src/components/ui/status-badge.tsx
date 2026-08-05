import { cn } from '@/lib/utils';
import { JobStatus } from '@workspace/api-client-react';

interface StatusBadgeProps {
  status: JobStatus | string;
  className?: string;
}

const statusStyles = {
  pending: 'bg-gray-500/10 text-gray-400 border-gray-500/20',
  processing: 'bg-blue-500/10 text-blue-400 border-blue-500/20 pulse-processing',
  completed: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  failed: 'bg-red-500/10 text-red-400 border-red-500/20',
  cancelled: 'bg-orange-500/10 text-orange-400 border-orange-500/20',
};

export function StatusBadge({ status, className }: StatusBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-mono font-medium border uppercase tracking-wide',
        statusStyles[status as keyof typeof statusStyles] || statusStyles.pending,
        className
      )}
      data-testid={`badge-status-${status}`}
    >
      {status}
    </span>
  );
}
