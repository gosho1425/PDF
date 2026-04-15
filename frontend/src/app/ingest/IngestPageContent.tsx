'use client';

import { useState, useRef } from 'react';
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
  WifiOff,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { ingestApi, jobsApi } from '@/lib/api';
import type { ScanSummary, IngestStatus } from '@/types';
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

// ── sub-component: FolderStatusCard ───────────────────────────────────────────

interface FolderStatusCardProps {
  isLoading: boolean;
  isError: boolean;
  isFetching: boolean;
  errorMessage: string | null;
  data: IngestStatus | undefined;
  apiBaseUrl: string;
  onRefresh: () => void;
}

function FolderStatusCard({
  isLoading,
  isError,
  isFetching,
  errorMessage,
  data,
  apiBaseUrl,
  onRefresh,
}: FolderStatusCardProps) {
  const [showDiag, setShowDiag] = useState(false);

  // Three explicit states — do NOT conflate them:
  // 1. isLoading  → first fetch in progress
  // 2. isError    → network/CORS/500 error — API unreachable
  // 3. data       → API responded; data.mounted tells us the real status
  const mounted = data?.mounted === true;
  const notMounted = data?.mounted === false;
  const isFallback = data?.is_fallback_mount === true;

  // ── badge ──────────────────────────────────────────────────────────────────
  let badge: React.ReactNode = null;
  if (isLoading) {
    badge = (
      <span className="badge bg-gray-100 text-gray-500 border-gray-200 text-xs">
        Checking…
      </span>
    );
  } else if (isError) {
    badge = (
      <span className="badge bg-red-100 text-red-700 border-red-200 text-xs">
        ✗ API unreachable
      </span>
    );
  } else if (mounted && !isFallback) {
    badge = (
      <span className="badge bg-green-100 text-green-700 border-green-200 text-xs">
        ✓ Mounted
      </span>
    );
  } else if (mounted && isFallback) {
    badge = (
      <span className="badge bg-amber-100 text-amber-700 border-amber-200 text-xs">
        ⚠ Fallback (empty)
      </span>
    );
  } else if (notMounted) {
    badge = (
      <span className="badge bg-amber-100 text-amber-700 border-amber-200 text-xs">
        ⚠ Not mounted
      </span>
    );
  }

  // ── icon background ────────────────────────────────────────────────────────
  const iconBg = isLoading
    ? 'bg-gray-100'
    : isError
    ? 'bg-red-100'
    : mounted && !isFallback
    ? 'bg-green-100'
    : 'bg-amber-100';

  const iconEl = isLoading ? (
    <Loader2 className="w-5 h-5 text-gray-400 animate-spin" />
  ) : isError ? (
    <WifiOff className="w-5 h-5 text-red-500" />
  ) : mounted && !isFallback ? (
    <FolderOpen className="w-5 h-5 text-green-600" />
  ) : (
    <FolderOpen className="w-5 h-5 text-amber-600" />
  );

  // ── card border ────────────────────────────────────────────────────────────
  const cardBorder = isError
    ? 'border-red-300 bg-red-50'
    : (notMounted || isFallback)
    ? 'border-amber-300 bg-amber-50'
    : '';

  return (
    <div className={cn('card p-6', cardBorder)}>
      <div className="flex items-start gap-4">
        {/* Icon */}
        <div className={cn('w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0', iconBg)}>
          {iconEl}
        </div>

        <div className="flex-1 min-w-0">
          {/* Title + badge */}
          <div className="flex items-center gap-2 flex-wrap">
            <h2 className="font-medium text-gray-800">Ingestion Folder</h2>
            {isFetching && !isLoading && (
              <Loader2 className="w-3.5 h-3.5 text-gray-400 animate-spin" />
            )}
            {badge}
          </div>

          {/* Path */}
          {data && (
            <p className="text-sm text-gray-600 mt-1 font-mono break-all">
              {data.ingest_dir}
            </p>
          )}

          {/* Mounted + PDF count */}
          {mounted && !isFallback && data?.pdf_count_in_folder !== null && (
            <p className={cn(
              'text-xs font-medium mt-0.5',
              (data?.pdf_count_in_folder ?? 0) > 0 ? 'text-green-700' : 'text-gray-500'
            )}>
              {data?.pdf_count_in_folder === 0
                ? 'Folder is mounted but empty — add PDFs, then click Scan Now.'
                : `${data?.pdf_count_in_folder} PDF${data?.pdf_count_in_folder !== 1 ? 's' : ''} found in folder`}
            </p>
          )}

          {/* Mount error detail */}
          {notMounted && data?.mount_error && (
            <p className="text-xs text-amber-800 mt-1 break-all">
              {data.mount_error}
            </p>
          )}

          {/* API error */}
          {isError && (
            <div className="mt-2">
              <p className="text-xs text-red-700 font-medium">
                The frontend cannot reach the backend API.
              </p>
              {errorMessage && (
                <p className="text-xs font-mono text-red-800 mt-0.5 break-all">
                  {errorMessage}
                </p>
              )}
              <p className="text-xs text-red-600 mt-1">
                Expected API at:{' '}
                <code className="font-mono bg-red-100 px-1 rounded">
                  {apiBaseUrl}/api/v1/papers/ingest-status
                </code>
              </p>
            </div>
          )}
        </div>

        {/* Refresh button */}
        <button
          onClick={onRefresh}
          disabled={isFetching}
          className="btn-secondary text-xs flex items-center gap-1.5 flex-shrink-0"
          title="Re-check mount status"
        >
          <RefreshCw className={cn('w-3 h-3', isFetching && 'animate-spin')} />
          Refresh
        </button>
      </div>

      {/* ── API error: recovery steps ──────────────────────────────────────── */}
      {isError && (
        <div className="mt-4 pt-4 border-t border-red-200 space-y-2">
          <p className="text-xs font-semibold text-red-800">How to fix — API unreachable:</p>
          <ol className="space-y-1.5 text-xs text-red-900">
            <li className="flex gap-2">
              <span className="font-bold shrink-0">1.</span>
              <span>
                Check all containers are running:{' '}
                <code className="font-mono bg-red-100 px-1 rounded">docker compose ps</code>
                — look for <code className="font-mono">pdf-api-1</code> as{' '}
                <code className="font-mono">running</code>.
              </span>
            </li>
            <li className="flex gap-2">
              <span className="font-bold shrink-0">2.</span>
              <span>
                Visit{' '}
                <a
                  href={`${apiBaseUrl}/health`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline text-red-700"
                >
                  {apiBaseUrl}/health
                </a>{' '}
                in your browser. If it fails, the API container is not running.
              </span>
            </li>
            <li className="flex gap-2">
              <span className="font-bold shrink-0">3.</span>
              <span>
                Read API logs:{' '}
                <code className="font-mono bg-red-100 px-1 rounded">docker compose logs api</code>
              </span>
            </li>
            <li className="flex gap-2">
              <span className="font-bold shrink-0">4.</span>
              <span>
                If the API is running but the browser still shows this error, check that{' '}
                <code className="font-mono bg-red-100 px-1 rounded">NEXT_PUBLIC_API_URL</code>{' '}
                in <code className="font-mono bg-red-100 px-1 rounded">.env</code> equals{' '}
                <code className="font-mono bg-red-100 px-1 rounded">http://localhost:8000</code>,
                then rebuild:{' '}
                <code className="font-mono bg-red-100 px-1 rounded">
                  docker compose up -d --build frontend
                </code>
              </span>
            </li>
          </ol>
        </div>
      )}

      {/* ── Not mounted: fix checklist ─────────────────────────────────────── */}
      {!isError && notMounted && (
        <div className="mt-4 pt-4 border-t border-amber-200 space-y-3">
          {data?.mount_error && (
            <div className="bg-red-50 border border-red-200 rounded p-2.5">
              <p className="text-xs font-semibold text-red-700 mb-0.5">Container error:</p>
              <p className="text-xs font-mono text-red-800 break-all">{data.mount_error}</p>
            </div>
          )}
          <p className="text-xs font-semibold text-amber-800">
            Fix checklist — work through in order, then click Refresh:
          </p>
          <ol className="space-y-2 text-xs text-amber-900">
            <li className="flex gap-2">
              <span className="font-bold shrink-0">1.</span>
              <span>
                In <code className="font-mono bg-amber-100 px-1 rounded">.env</code>,
                set <code className="font-mono bg-amber-100 px-1 rounded">HOST_PAPER_DIR</code>{' '}
                to the full path of your PDF folder.{' '}
                <strong>No <code>#&nbsp;comments</code> or trailing spaces</strong> on that line.
                <br />
                <code className="font-mono bg-amber-100 rounded px-1 mt-0.5 inline-block">
                  HOST_PAPER_DIR=C:\Users\YourName\Documents\papers
                </code>
              </span>
            </li>
            <li className="flex gap-2">
              <span className="font-bold shrink-0">2.</span>
              <span>
                On Windows, ensure this line is also in{' '}
                <code className="font-mono bg-amber-100 px-1 rounded">.env</code>:
                <br />
                <code className="font-mono bg-amber-100 rounded px-1 mt-0.5 inline-block">
                  COMPOSE_CONVERT_WINDOWS_PATHS=1
                </code>
              </span>
            </li>
            <li className="flex gap-2">
              <span className="font-bold shrink-0">3.</span>
              <span>
                Make sure the folder <strong>actually exists</strong> on your host machine
                (create it if needed and add a test PDF).
              </span>
            </li>
            <li className="flex gap-2">
              <span className="font-bold shrink-0">4.</span>
              <span>Restart Docker to apply the new volume mount:</span>
            </li>
          </ol>
          <code className="block font-mono bg-amber-100 rounded px-3 py-2 text-xs text-amber-900">
            docker compose down &amp;&amp; docker compose up -d
          </code>
          <p className="text-xs text-amber-700">
            Then click <strong>Refresh</strong> above. If still not mounted, open{' '}
            <a
              href={`${apiBaseUrl}/api/v1/papers/ingest-status`}
              target="_blank"
              rel="noopener noreferrer"
              className="underline text-amber-700"
            >
              {apiBaseUrl}/api/v1/papers/ingest-status
            </a>{' '}
            in your browser and check the <code className="font-mono">mount_error</code> field.
          </p>
        </div>
      )}

      {/* ── Fallback mount warning ─────────────────────────────────────────── */}
      {!isError && isFallback && mounted && (
        <div className="mt-4 pt-4 border-t border-amber-200 space-y-2">
          <p className="text-xs font-semibold text-amber-800">
            Using the fallback empty folder (HOST_PAPER_DIR not configured)
          </p>
          <p className="text-xs text-amber-900">
            The container is using the project's internal <code className="font-mono bg-amber-100 px-1 rounded">data/ingest</code>{' '}
            directory, which is empty. To use your own PDFs:
          </p>
          <ol className="space-y-1 text-xs text-amber-900">
            <li className="flex gap-2">
              <span className="font-bold shrink-0">1.</span>
              <span>
                Add to <code className="font-mono bg-amber-100 px-1 rounded">.env</code>:{' '}
                <code className="font-mono bg-amber-100 px-1 rounded">HOST_PAPER_DIR=C:\path\to\your\pdfs</code>
              </span>
            </li>
            <li className="flex gap-2">
              <span className="font-bold shrink-0">2.</span>
              <span>
                Run:{' '}
                <code className="font-mono bg-amber-100 px-1 rounded">
                  docker compose down &amp;&amp; docker compose up -d
                </code>
              </span>
            </li>
          </ol>
          <p className="text-xs text-amber-700">
            Alternatively, copy PDF files directly into{' '}
            <code className="font-mono bg-amber-100 px-1 rounded">data/ingest/</code>{' '}
            in the project folder and click <strong>Scan Now</strong>.
          </p>
        </div>
      )}

      {/* ── Diagnostics panel ─────────────────────────────────────────────── */}
      <div className="mt-3 pt-3 border-t border-gray-100">
        <button
          onClick={() => setShowDiag((v) => !v)}
          className="text-xs text-gray-400 hover:text-gray-600 flex items-center gap-1"
        >
          {showDiag ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          {showDiag ? 'Hide' : 'Show'} diagnostics
        </button>
        {showDiag && (
          <div className="mt-2 bg-gray-50 rounded p-3 text-xs font-mono text-gray-600 space-y-1 break-all">
            <p>
              <span className="text-gray-400">NEXT_PUBLIC_API_URL:</span>{' '}
              {apiBaseUrl}
            </p>
            <p>
              <span className="text-gray-400">ingest-status endpoint:</span>{' '}
              <a
                href={`${apiBaseUrl}/api/v1/papers/ingest-status`}
                target="_blank"
                rel="noopener noreferrer"
                className="underline text-blue-500"
              >
                {apiBaseUrl}/api/v1/papers/ingest-status
              </a>
            </p>
            <p>
              <span className="text-gray-400">query state:</span>{' '}
              {isLoading ? 'loading' : isError ? 'error' : 'success'}
            </p>
            {isError && errorMessage && (
              <p><span className="text-gray-400">fetch error:</span> {errorMessage}</p>
            )}
            {data && (
              <>
                <p><span className="text-gray-400">ingest_dir:</span> {data.ingest_dir}</p>
                <p><span className="text-gray-400">INGEST_DIR env (container):</span> {data.ingest_dir_from_env}</p>
                <p><span className="text-gray-400">mounted:</span> {String(data.mounted)}</p>
                <p><span className="text-gray-400">is_fallback_mount:</span> {String(data.is_fallback_mount)}</p>
                <p><span className="text-gray-400">pdf_count:</span> {String(data.pdf_count_in_folder)}</p>
                {data.mount_error && (
                  <p><span className="text-gray-400">mount_error:</span> {data.mount_error}</p>
                )}
                {data.hint && (
                  <p><span className="text-gray-400">hint:</span> {data.hint}</p>
                )}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ── main component ─────────────────────────────────────────────────────────────

export function IngestPageContent() {
  const queryClient = useQueryClient();

  const [scanHistory, setScanHistory] = useState<ScanRecord[]>([]);
  const [pollingTaskId, setPollingTaskId] = useState<string | null>(null);

  // ── Folder status ──────────────────────────────────────────────────────────
  const {
    data: ingestStatus,
    isLoading: statusLoading,
    isError: statusError,
    error: statusErrorObj,
    refetch: refetchStatus,
    isFetching: statusFetching,
  } = useQuery({
    queryKey: ['ingest-status'],
    queryFn: ingestApi.getStatus,
    refetchInterval: 30_000,
    retry: 3,
    retryDelay: 2000,
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
      queryClient.invalidateQueries({ queryKey: ['papers-summary'] });
      queryClient.invalidateQueries({ queryKey: ['papers'] });
      queryClient.invalidateQueries({ queryKey: ['ingest-status'] });
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

  // Whether the folder is truly ready to scan
  const isMounted = ingestStatus?.mounted === true;

  const apiErrorMessage = statusError
    ? (statusErrorObj as Error)?.message || 'Failed to reach the backend API'
    : null;

  const apiBaseUrl =
    typeof process !== 'undefined'
      ? process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      : 'http://localhost:8000';

  // ── render ─────────────────────────────────────────────────────────────────

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
        <FolderStatusCard
          isLoading={statusLoading}
          isError={statusError}
          isFetching={statusFetching}
          errorMessage={apiErrorMessage}
          data={ingestStatus}
          apiBaseUrl={apiBaseUrl}
          onRefresh={refetchStatus}
        />

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
              disabled={scanning || !isMounted}
              className={cn(
                'btn-primary flex items-center gap-2 min-w-[140px] justify-center',
                !isMounted && 'opacity-50 cursor-not-allowed'
              )}
              title={
                statusLoading ? 'Checking folder status…' :
                statusError ? 'Cannot reach the API' :
                !isMounted ? 'Mount the ingestion folder first' :
                undefined
              }
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
            <p>
              1. Set <code className="font-mono bg-blue-100 px-1 rounded">HOST_PAPER_DIR</code> in{' '}
              <code className="font-mono bg-blue-100 px-1 rounded">.env</code> to the host folder
              containing your PDFs (no inline comments or trailing spaces).
            </p>
            <p>
              2. On Windows, also set{' '}
              <code className="font-mono bg-blue-100 px-1 rounded">COMPOSE_CONVERT_WINDOWS_PATHS=1</code>{' '}
              in <code className="font-mono bg-blue-100 px-1 rounded">.env</code>.
            </p>
            <p>3. Restart: <code className="font-mono bg-blue-100 px-1 rounded">docker compose down &amp;&amp; docker compose up -d</code></p>
            <p>4. Click <strong>Scan Now</strong> — or call <code className="font-mono bg-blue-100 px-1 rounded">POST /api/v1/papers/scan</code>.</p>
            <p>5. Each PDF is hashed (SHA-256). Already-ingested files are skipped; new ones are queued for parsing and AI extraction.</p>
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
