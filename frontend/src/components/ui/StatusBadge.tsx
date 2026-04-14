import { cn, STATUS_COLORS, STATUS_LABELS } from '@/lib/utils';
import type { PaperStatus } from '@/types';

interface StatusBadgeProps {
  status: PaperStatus;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  return (
    <span className={cn('badge', STATUS_COLORS[status], className)}>
      {STATUS_LABELS[status]}
    </span>
  );
}
