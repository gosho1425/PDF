'use client';

import { useState, useCallback, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  FolderOpen,
  RefreshCw,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Activity,
  Clock,
  FileText,
  SkipForward,
  Info,
  Loader2,
} from 'lucide-react';
import { ingestApi, jobsApi } from '@/lib/api';
import type { ScanSummary } from '@/types';
import toast from 'react-hot-toast';
import { cn } from '@/lib/utils';

// ── helpers ────────────────────────────────────────────────────────────────────

function formatDateTime(iso: string) {
  return new Intl.DateTimeFormat('en-GB', {
    dateStyle: 'short',
    timeStyle: 'medium',
  }).format(new Date(iso));
}

// ── types ──────────────────────────────────────────────────────────────────────

interface ScanRecord {
  taskId: string;
  startedAt: string;
  summary?: ScanSummary;
  celeryState?: string;
}

// ── component ─────────────────────────────────────────────────────────────────

export function IngestPageContent() {
  const queryClient = useQueryClient();

  // Keep a list of scan task IDs so we can poll each one
  const [scanHistory, setScanHistory] = useState<ScanRecord[]>([]);
  const [pollingTaskId, setPollingTaskId] = useState<string | null>(null);

  // ── Folder status ──────────────────────────────────────────────────────────
  const { data: ingestStatus, isLoading: statusLoading, refetch: refetchStatus } = useQuery({
    queryKey: ['ingest-status'],
    queryFn: ingestApi.getStatus,
    refetchInterval: 30_000, // recheck mount every 30 s
  });

  // ── Trigger scan ───────────────────────────────────────────────────────────
  const scanMutation = useMutation({
    mutationFn: ingestApi.triggerScan,
    onSuccess: (result) => {
      const record: ScanRecord = {
        taskId: result.task_id,
        startedAt: new Date().toISOString(),
      };
      setScanHistory((prev) => [record, ...prev]);
      setPollingTaskId(result.task_id);
      toast.success('Scan started — check the log below for progress');
    },
    onError: (err: Error) => {
      toast.error(err.message || 'Failed to start scan');
    },
  });

  // ── Poll active task ───────────────────────────────────────────────────────
  const { data: taskStatus } = useQuery({
    queryKey: ['celery-task', pollingTaskId],
    queryFn: () => jobsApi.getCeleryStatus(pollingTaskId!),
    enabled: !!pollingTaskId,
    refetchInterval: (query) => {
      const state = query.state.data?.state;
      if (state === 'SUCCESS' || state === 'FAILURE') return false;
      return 2000;
    },
    select: (data) => data,
  });

  // Sync task result into scanHistory
  const prevTaskStatusRef = useRef<string | undefined>(undefined);
  if (
    taskStatus &&
    pollingTaskId &&
    taskStatus.state !== prevTaskStatusRef.current
  ) {
    prevTaskStatusRef.current = taskStatus.state;
    if (taskStatus.state === 'SUCCESS' || taskStatus.state === 'FAILURE') {
      setScanHistory((prev) =>
        prev.map((r) =>
          r.taskId === pollingTaskId
            ? { ...r, summary: taskStatus.result, celeryState: taskStatus.state }
            : r
        )
      );
      // Refresh papers list so the dashboard updates immediately
      queryClient.invalidateQueries({ queryKey: ['papers-summary'] });
      queryClient.invalidateQueries({ queryKey: ['papers'] });
      setPollingTaskId(null);
    } else {
      setScanHistory((prev) =>
        prev.map((r) =>
          r.taskId === pollingTaskId
            ? { ...r, celeryState: taskStatus.state }
            : r
        )
      );
    }
  }

  const scanning = scanMutation.isPending || !!pollingTaskId;

  // ── render ─────────────────────────────────────────────────────────────────

  const mounted = ingestStatus?.mounted;

  return (
    <div className="p-8 max-w-4xl">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-gray-900">PDF Ingestion</h1>
        <p className="text-sm text-gray-500 mt-1">
          Scan the configured host folder for new PDF files. Duplicates are
          detected by SHA-256 and skipped automatically.
        </p>
      </div>

      <div className="space-y-6">

        {/* ── Folder mount status card ──────────────────────────────────────── */}
        <div className={cn('card p-6', !mounted && 'border-amber-300 bg-amber-50')}>
          <div className="flex items-start gap-4">
            <div
              className={cn(
                'w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0',
                mounted ? 'bg-green-100' : 'bg-amber-100'
              )}
            >
              <FolderOpen
                className={cn('w-5 h-5', mounted ? 'text-green-600' : 'text-amber-600')}
              />
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h2 className="font-medium text-gray-800">Ingestion Folder</h2>
                {statusLoading && (
                  <Loader2 className="w-3.5 h-3.5 text-gray-400 animate-spin" />
                )}
                {!statusLoading && mounted && (
                  <span className="badge bg-green-100 text-green-700 border-green-200 text-xs">
                    ✓ Mounted
                  </span>
                )}
                {!statusLoading && !mounted && (
                  <span className="badge bg-amber-100 text-amber-700 border-amber-200 text-xs">
                    ⚠ Not mounted
                  </span>
                )}
              </div>

              {ingestStatus && (
                <>
                  <p className="text-sm text-gray-600 mt-1 font-mono break-all">
                    {ingestStatus.ingest_dir}
                  </p>
                  {mounted && ingestStatus.pdf_count_in_folder !== null && (
                    <p className="text-xs text-gray-500 mt-0.5">
                      {ingestStatus.pdf_count_in_folder} PDF
                      {ingestStatus.pdf_count_in_folder !== 1 ? 's' : ''} found in folder
                    </p>
                  )}
                  {!mounted && ingestStatus.hint && (
                    <p className="text-xs text-amber-700 mt-2 leading-relaxed">
                      {ingestStatus.hint}
                    </p>
                  )}
                </>
              )}
            </div>

            <button
              onClick={() => refetchStatus()}
              className="btn-secondary text-xs flex items-center gap-1.5 flex-shrink-0"
            >
              <RefreshCw className="w-3 h-3" />
              Refresh
            </button>
          </div>

          {/* Detailed fix instructions when not mounted */}
          {!mounted && (
            <div className="mt-4 pt-4 border-t border-amber-200 space-y-3">

              {/* OS-level error from backend */}
              {ingestStatus?.mount_error && (
                <div className="bg-red-50 border border-red-200 rounded p-2.5">
                  <p className="text-xs font-semibold text-red-700 mb-0.5">Container error:</p>
                  <p className="text-xs font-mono text-red-800 break-all">{ingestStatus.mount_error}</p>
                </div>
              )}

              <p className="text-xs font-semibold text-amber-800">
                Fix checklist — work through these steps in order:
              </p>

              <ol className="space-y-2 text-xs text-amber-900">
                <li className="flex gap-2">
                  <span className="font-bold shrink-0">1.</span>
                  <span>
                    Open your <code className="font-mono bg-amber-100 px-1 rounded">.env</code> file and set{' '}
                    <code className="font-mono bg-amber-100 px-1 rounded">HOST_PAPER_DIR</code> to your PDF folder path.
                    <br />
                    <span className="text-amber-700">
                      ⚠ No inline comments! Everything after <code className="font-mono">=</code> on that line
                      is the path. Remove any <code className="font-mono"># comment</code> or trailing spaces.
                    </span>
                  </span>
                </li>
                <li className="flex gap-2">
                  <span className="font-bold shrink-0">2.</span>
                  <span>
                    On <strong>Windows</strong>, also add this line to <code className="font-mono bg-amber-100 px-1 rounded">.env</code>:
                    <br />
                    <code className="font-mono bg-amber-100 px-1 rounded">COMPOSE_CONVERT_WINDOWS_PATHS=1</code>
                    <br />
                    <span className="text-amber-700">This tells Docker Compose to convert <code>C:\…</code> paths correctly.</span>
                  </span>
                </li>
                <li className="flex gap-2">
                  <span className="font-bold shrink-0">3.</span>
                  <span>
                    Make sure the folder actually exists on your machine. Create it if needed.
                  </span>
                </li>
                <li className="flex gap-2">
                  <span className="font-bold shrink-0">4.</span>
                  <span>
                    Restart Docker Compose to apply the new volume mount:
                    <br />
                    <code className="font-mono bg-amber-100 px-1 rounded block mt-1 py-1">
                      docker compose down &amp;&amp; docker compose up -d
                    </code>
                  </span>
                </li>
                <li className="flex gap-2">
                  <span className="font-bold shrink-0">5.</span>
                  <span>
                    Come back here and click <strong>Refresh</strong> — the status should turn green.
                  </span>
                </li>
              </ol>

              <div className="bg-amber-100 rounded p-3 text-xs font-mono space-y-0.5 text-amber-900">
                <p className="text-amber-700 font-sans font-semibold not-italic">
                  Correct .env entries (Windows):
                </p>
                <p>HOST_PAPER_DIR=C:\Users\YourName\Documents\papers</p>
                <p>INGEST_DIR=/ingest</p>
                <p>COMPOSE_CONVERT_WINDOWS_PATHS=1</p>
                <p className="mt-1 text-amber-700 font-sans font-semibold not-italic">
                  macOS / Linux:
                </p>
                <p>HOST_PAPER_DIR=/home/yourname/papers</p>
                <p>INGEST_DIR=/ingest</p>
              </div>
            </div>
          )}
        </div>

        {/* ── Scan Now button ──────────────────────────────────────────────── */}
        <div className="card p-6">
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div>
              <h2 className="font-medium text-gray-800">Scan for New PDFs</h2>
              <p className="text-xs text-gray-500 mt-0.5">
                Runs recursively through the folder. Already-ingested files are
                identified by SHA-256 hash and silently skipped.
              </p>
            </div>

            <button
              onClick={() => scanMutation.mutate()}
              disabled={scanning || !mounted}
              className={cn(
                'btn-primary flex items-center gap-2 min-w-[140px] justify-center',
                (!mounted) && 'opacity-50 cursor-not-allowed'
              )}
              title={!mounted ? 'Mount the ingestion folder first' : undefined}
            >
              {scanning ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Scanning…
                </>
              ) : (
                <>
                  <Activity className="w-4 h-4" />
                  Scan Now
                </>
              )}
            </button>
          </div>
        </div>

        {/* ── Scan history / log ───────────────────────────────────────────── */}
        {scanHistory.length > 0 && (
          <div className="card overflow-hidden">
            <div className="px-5 py-3 border-b border-gray-100 flex items-center gap-2">
              <Clock className="w-4 h-4 text-gray-400" />
              <h3 className="font-medium text-gray-700 text-sm">Scan Log</h3>
              <span className="badge bg-gray-100 text-gray-600 border-gray-200 text-xs ml-auto">
                {scanHistory.length} run{scanHistory.length !== 1 ? 's' : ''}
              </span>
            </div>

            <div className="divide-y divide-gray-50">
              {scanHistory.map((record) => (
                <ScanHistoryRow key={record.taskId} record={record} />
              ))}
            </div>
          </div>
        )}

        {/* ── How it works info box ────────────────────────────────────────── */}
        <div className="flex gap-3 bg-blue-50 border border-blue-100 rounded-lg p-4">
          <Info className="w-4 h-4 text-blue-500 flex-shrink-0 mt-0.5" />
          <div className="text-xs text-blue-700 space-y-1">
            <p className="font-semibold">How folder-based ingestion works</p>
            <p>1. Place PDF files in the host folder configured as <code className="font-mono bg-blue-100 px-1 rounded">HOST_PAPER_DIR</code> in <code className="font-mono bg-blue-100 px-1 rounded">.env</code> (no inline comments or trailing spaces on that line).</p>
            <p>2. Click <strong>Scan Now</strong> — or set up a scheduled job to call <code className="font-mono bg-blue-100 px-1 rounded">POST /api/v1/papers/scan</code>.</p>
            <p>3. Each PDF is hashed (SHA-256). Already-ingested files are skipped; new ones are queued.</p>
            <p>4. The Celery worker parses the PDF, calls Claude 3.5 Sonnet for extraction, and stores results in PostgreSQL.</p>
            <p>5. View results in <strong>Papers</strong> or export via <strong>Data Table</strong>.</p>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── ScanHistoryRow sub-component ──────────────────────────────────────────────

function ScanHistoryRow({ record }: { record: ScanRecord }) {
  const { summary, celeryState, startedAt, taskId } = record;

  const isRunning = !summary && celeryState !== 'FAILURE';
  const isFailed = celeryState === 'FAILURE';

  return (
    <div className="px-5 py-4">
      {/* Row header */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            {isRunning && !isFailed && (
              <Loader2 className="w-3.5 h-3.5 text-brand-500 animate-spin flex-shrink-0" />
            )}
            {summary && !isFailed && (
              <CheckCircle className="w-3.5 h-3.5 text-green-500 flex-shrink-0" />
            )}
            {isFailed && (
              <XCircle className="w-3.5 h-3.5 text-red-500 flex-shrink-0" />
            )}
            <span className="text-xs font-medium text-gray-700">
              {isRunning && !isFailed
                ? `Running… (${celeryState ?? 'PENDING'})`
                : isFailed
                ? 'Scan failed'
                : 'Scan complete'}
            </span>
          </div>
          <p className="text-xs text-gray-400 mt-0.5">
            Started {formatDateTime(startedAt)} · task&nbsp;
            <code className="font-mono text-gray-500">{taskId.slice(0, 8)}…</code>
          </p>
        </div>
      </div>

      {/* Stats grid */}
      {summary && (
        <div className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-2">
          <StatChip
            icon={<FileText className="w-3.5 h-3.5" />}
            label="Found"
            value={summary.found}
            color="text-gray-700"
            bg="bg-gray-50"
          />
          <StatChip
            icon={<CheckCircle className="w-3.5 h-3.5" />}
            label="Ingested"
            value={summary.ingested}
            color="text-green-700"
            bg="bg-green-50"
          />
          <StatChip
            icon={<SkipForward className="w-3.5 h-3.5" />}
            label="Skipped"
            value={summary.skipped_duplicates}
            color="text-blue-700"
            bg="bg-blue-50"
          />
          <StatChip
            icon={<AlertTriangle className="w-3.5 h-3.5" />}
            label="Failed"
            value={summary.failed}
            color="text-red-700"
            bg="bg-red-50"
          />
        </div>
      )}

      {/* Error list */}
      {summary && summary.errors.length > 0 && (
        <div className="mt-3 space-y-1">
          {summary.errors.map((err, i) => (
            <p key={i} className="text-xs text-red-600 bg-red-50 px-2 py-1 rounded font-mono truncate">
              {err}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}

function StatChip({
  icon, label, value, color, bg,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  color: string;
  bg: string;
}) {
  return (
    <div className={cn('rounded-lg px-3 py-2 flex items-center gap-2', bg)}>
      <span className={color}>{icon}</span>
      <div>
        <div className={cn('text-base font-bold tabular-nums leading-none', color)}>
          {value}
        </div>
        <div className="text-xs text-gray-500 mt-0.5">{label}</div>
      </div>
    </div>
  );
}
