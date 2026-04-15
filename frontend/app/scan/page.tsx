'use client';

import { useState, useEffect } from 'react';
import { scanApi, settingsApi } from '@/lib/api';
import type { ScanResult, AppSettings } from '@/types';
import toast from 'react-hot-toast';
import {
  ScanLine, CheckCircle, SkipForward, XCircle,
  FileSearch, Clock, AlertTriangle, FolderOpen
} from 'lucide-react';
import Link from 'next/link';

export default function ScanPage() {
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [result, setResult] = useState<ScanResult | null>(null);
  const [scanning, setScanning] = useState(false);
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    settingsApi.get().then(setSettings).catch(() => {});
    scanApi.status().then(s => s.last_result && setResult(s.last_result)).catch(() => {});
  }, []);

  // Tick timer while scanning
  useEffect(() => {
    if (!scanning) { setElapsed(0); return; }
    const id = setInterval(() => setElapsed(e => e + 1), 1000);
    return () => clearInterval(id);
  }, [scanning]);

  const runScan = async () => {
    if (!settings?.paper_folder) {
      toast.error('No folder configured. Go to Settings first.');
      return;
    }
    if (settings.folder_status !== 'ok') {
      toast.error('Folder not accessible. Check Settings.');
      return;
    }
    setScanning(true);
    setResult(null);
    try {
      const r = await scanApi.run();
      setResult(r);
      if (r.new_processed > 0) {
        toast.success(`Scan complete — ${r.new_processed} new paper(s) processed!`);
      } else if (r.total_found === 0) {
        toast('No PDFs found in folder.', { icon: '📁' });
      } else {
        toast(`Scan complete — all ${r.total_found} PDFs already processed.`, { icon: '✓' });
      }
    } catch (e: any) {
      toast.error(`Scan failed: ${e.message}`);
    } finally {
      setScanning(false);
    }
  };

  const folderOk = settings?.folder_status === 'ok';

  return (
    <div className="max-w-2xl space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Scan for PDFs</h1>
        <p className="text-gray-500 mt-1">
          Recursively scan the configured folder, skip already-processed files,
          and extract structured data from new PDFs using AI.
        </p>
      </div>

      {/* Folder status */}
      <div className="card p-5">
        <div className="flex items-start gap-3">
          <FolderOpen className={`w-5 h-5 flex-shrink-0 mt-0.5 ${folderOk ? 'text-green-500' : 'text-amber-500'}`} />
          <div>
            <h2 className="font-semibold text-gray-800">Configured Folder</h2>
            <p className="font-mono text-sm text-gray-600 mt-0.5 break-all">
              {settings?.paper_folder || '(not set)'}
            </p>
            {folderOk && (
              <p className="text-xs text-green-700 mt-1">
                ✓ Accessible · {settings?.pdf_count} PDF(s) found
              </p>
            )}
            {settings && !folderOk && (
              <p className="text-xs text-amber-700 mt-1">
                ⚠ {settings.folder_status === 'not_set' ? 'No folder configured' : 'Folder not found'}.{' '}
                <Link href="/settings" className="underline">Go to Settings →</Link>
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Scan button */}
      <div className="card p-6">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div>
            <h2 className="font-semibold text-gray-800">Start Scan</h2>
            <p className="text-xs text-gray-500 mt-0.5">
              New files are detected by SHA-256. Already-processed files are skipped.
              LLM extraction can take 30–120 seconds per paper.
            </p>
          </div>
          <button
            onClick={runScan}
            disabled={scanning || !folderOk}
            className="btn-primary min-w-[140px] justify-center"
            title={!folderOk ? 'Configure the folder in Settings first' : undefined}
          >
            {scanning ? (
              <>
                <Clock className="w-4 h-4 animate-spin" />
                Scanning… {elapsed}s
              </>
            ) : (
              <>
                <ScanLine className="w-4 h-4" />
                Scan Now
              </>
            )}
          </button>
        </div>

        {scanning && (
          <div className="mt-4 bg-blue-50 rounded-lg p-4 text-sm text-blue-800">
            <p className="font-medium">Scan in progress…</p>
            <p className="text-xs mt-1 text-blue-600">
              The LLM is reading each new PDF. This window will update when complete.
              Do not close this tab.
            </p>
          </div>
        )}
      </div>

      {/* Result */}
      {result && !scanning && (
        <div className="card overflow-hidden">
          <div className="px-5 py-3 bg-gray-50 border-b border-gray-100">
            <h3 className="font-semibold text-gray-800">Scan Result</h3>
            <p className="text-xs text-gray-500 mt-0.5">
              Completed in {result.duration_seconds}s
            </p>
          </div>
          <div className="p-5">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <ResultChip icon={<FileSearch />} label="Found" value={result.total_found} color="gray" />
              <ResultChip icon={<CheckCircle />} label="New" value={result.new_processed} color="green" />
              <ResultChip icon={<SkipForward />} label="Skipped" value={result.skipped} color="blue" />
              <ResultChip icon={<XCircle />} label="Failed" value={result.failed} color="red" />
            </div>

            {result.errors.length > 0 && (
              <div className="mt-4">
                <h4 className="text-sm font-medium text-red-700 flex items-center gap-1.5 mb-2">
                  <AlertTriangle className="w-4 h-4" />
                  Errors ({result.errors.length})
                </h4>
                <div className="space-y-1">
                  {result.errors.map((e, i) => (
                    <p key={i} className="text-xs font-mono text-red-600 bg-red-50 px-2 py-1.5 rounded break-all">
                      {e}
                    </p>
                  ))}
                </div>
              </div>
            )}

            {result.new_processed > 0 && (
              <div className="mt-4">
                <Link href="/papers" className="btn-primary text-sm inline-flex">
                  <CheckCircle className="w-4 h-4" />
                  View Processed Papers →
                </Link>
              </div>
            )}
          </div>
        </div>
      )}

      {/* How it works */}
      <div className="bg-blue-50 border border-blue-100 rounded-xl p-4 text-sm text-blue-800 space-y-1">
        <p className="font-semibold">How scanning works</p>
        <p>1. The backend reads your configured folder recursively for all .pdf files.</p>
        <p>2. Each file is SHA-256 hashed — already-processed files are skipped instantly.</p>
        <p>3. New PDFs are read with pdfplumber, then sent to the AI model for extraction.</p>
        <p>4. Results are saved to SQLite + as .txt summary and .json extraction files.</p>
        <p>5. Extracted input/output variables are structured for Bayesian optimization.</p>
      </div>
    </div>
  );
}

function ResultChip({ icon, label, value, color }: {
  icon: React.ReactNode; label: string; value: number;
  color: 'gray' | 'green' | 'blue' | 'red';
}) {
  const cls = {
    gray: 'bg-gray-50 text-gray-700',
    green: 'bg-green-50 text-green-700',
    blue: 'bg-blue-50 text-blue-700',
    red: 'bg-red-50 text-red-700',
  }[color];
  return (
    <div className={`rounded-lg p-3 ${cls}`}>
      <div className="flex items-center gap-1.5 text-xs font-medium mb-1 opacity-70">
        <span className="w-3.5 h-3.5">{icon}</span>
        {label}
      </div>
      <p className="text-2xl font-bold">{value}</p>
    </div>
  );
}
