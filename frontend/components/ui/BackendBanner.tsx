'use client';

/**
 * BackendBanner
 *
 * Shown at the top of every page when the FastAPI backend is not reachable.
 * Polls /api/backend-status every 5 seconds and disappears automatically
 * once the backend comes online.
 */

import { useEffect, useState } from 'react';
import { AlertTriangle, CheckCircle, RefreshCw } from 'lucide-react';

interface StatusResult {
  ok: boolean;
  version?: string;
  reason?: string;
}

export default function BackendBanner() {
  const [status, setStatus] = useState<StatusResult | null>(null);
  const [checking, setChecking] = useState(false);

  const check = async () => {
    setChecking(true);
    try {
      const res = await fetch('/api/backend-status', { cache: 'no-store' });
      const data: StatusResult = await res.json();
      setStatus(data);
    } catch {
      setStatus({ ok: false, reason: 'Could not reach frontend server' });
    } finally {
      setChecking(false);
    }
  };

  useEffect(() => {
    check();
    // Auto-retry every 5 seconds while the backend is down
    const interval = setInterval(() => {
      if (status === null || !status.ok) check();
    }, 5000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status?.ok]);

  // Nothing to show while loading or when backend is fine
  if (status === null) return null;
  if (status.ok) return null;

  return (
    <div className="bg-red-50 border-b border-red-200 px-4 py-3">
      <div className="max-w-5xl mx-auto flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-red-800 text-sm">
            Backend not running — all API calls will fail
          </p>
          <p className="text-xs text-red-700 mt-0.5 break-words">
            {status.reason}
          </p>
          <div className="mt-2 font-mono text-xs bg-red-100 rounded px-2 py-1.5 space-y-0.5">
            <p className="text-red-800 font-semibold">Quick start (Windows):</p>
            <p className="text-red-700">1. Open a new Command Prompt</p>
            <p className="text-red-700">2. <span className="bg-red-200 px-1 rounded">cd path\to\paperlens\backend</span></p>
            <p className="text-red-700">3. <span className="bg-red-200 px-1 rounded">.venv\Scripts\activate</span></p>
            <p className="text-red-700">4. <span className="bg-red-200 px-1 rounded">uvicorn app.main:app --reload</span></p>
          </div>
        </div>
        <button
          onClick={check}
          disabled={checking}
          className="flex-shrink-0 text-xs text-red-600 hover:text-red-800 flex items-center gap-1 mt-0.5"
          title="Retry connection"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${checking ? 'animate-spin' : ''}`} />
          Retry
        </button>
      </div>
    </div>
  );
}
