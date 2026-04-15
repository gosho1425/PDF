import { PaperStatus } from '@/types';

const cfg: Record<PaperStatus, { label: string; cls: string }> = {
  pending:    { label: 'Pending',    cls: 'bg-gray-100 text-gray-600' },
  processing: { label: 'Processing', cls: 'bg-blue-100 text-blue-700' },
  done:       { label: 'Done',       cls: 'bg-green-100 text-green-700' },
  failed:     { label: 'Failed',     cls: 'bg-red-100 text-red-700' },
};

export function StatusBadge({ status }: { status: PaperStatus }) {
  const { label, cls } = cfg[status] ?? cfg.pending;
  return <span className={`badge ${cls}`}>{label}</span>;
}
