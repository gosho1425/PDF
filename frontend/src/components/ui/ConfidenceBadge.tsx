import { cn, confidenceColor, confidenceLabel } from '@/lib/utils';

interface ConfidenceBadgeProps {
  confidence: number | null;
  isInferred?: boolean;
  className?: string;
}

export function ConfidenceBadge({ confidence, isInferred, className }: ConfidenceBadgeProps) {
  return (
    <span className={cn('text-xs font-medium', confidenceColor(confidence), className)}>
      {confidence !== null ? `${Math.round(confidence * 100)}%` : '–'}
      {isInferred && (
        <span className="ml-1 text-gray-400 italic" title="Inferred, not directly stated">
          (inferred)
        </span>
      )}
    </span>
  );
}
