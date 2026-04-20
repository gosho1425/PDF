'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { papersApi, settingsApi, scanApi } from '@/lib/api';
import type { AppSettings, ScanResult } from '@/types';
import { BookOpen, ScanLine, Settings, FolderOpen, CheckCircle, AlertTriangle, Clock, TrendingUp } from 'lucide-react';

export default function DashboardPage() {
  const [appSettings, setAppSettings] = useState<AppSettings | null>(null);
  const [scanStatus, setScanStatus] = useState<{ running: boolean; last_result: ScanResult | null } | null>(null);
  const [paperCount, setPaperCount] = useState<number | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      settingsApi.get().catch(() => null),
      scanApi.status().catch(() => null),
      papersApi.list({ limit: 1 }).catch(() => null),
    ]).then(([s, sc, papers]) => {
      if (s) setAppSettings(s);
      if (sc) setScanStatus(sc);
      if (papers) setPaperCount(papers.total);
      if (!s && !sc) setApiError('Cannot reach backend API at localhost:8000. Is the backend running?');
    });
  }, []);

  const lr = scanStatus?.last_result;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500 mt-1">Local PDF extraction — no cloud infrastructure required.</p>
      </div>

      {apiError && (
        <div className="card p-4 border-red-300 bg-red-50">
          <div className="flex items-start gap-2">
            <AlertTriangle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-red-800">Backend not reachable</p>
              <p className="text-sm text-red-700 mt-0.5">{apiError}</p>
              <p className="text-xs text-red-600 mt-2 font-mono">
                Start it with: cd backend && uvicorn app.main:app --reload
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Stat cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard
          icon={<BookOpen className="w-6 h-6 text-blue-500" />}
          label="Total Papers"
          value={paperCount ?? '—'}
          sub="in database"
          bg="bg-blue-50"
        />
        <StatCard
          icon={<CheckCircle className="w-6 h-6 text-green-500" />}
          label="Last Scan — New"
          value={lr?.new_processed ?? '—'}
          sub={lr ? `${lr.skipped} skipped, ${lr.failed} failed` : 'no scan yet'}
          bg="bg-green-50"
        />
        <StatCard
          icon={<Clock className="w-6 h-6 text-purple-500" />}
          label="Last Scan — Duration"
          value={lr ? `${lr.duration_seconds}s` : '—'}
          sub={lr ? `${lr.total_found} PDFs found` : 'run a scan first'}
          bg="bg-purple-50"
        />
      </div>

      {/* Folder status */}
      <div className="card p-5">
        <div className="flex items-start gap-3">
          <FolderOpen className="w-5 h-5 text-gray-400 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <h2 className="font-semibold text-gray-800">Paper Folder</h2>
            {appSettings ? (
              <>
                <p className="font-mono text-sm text-gray-600 mt-0.5 break-all">
                  {appSettings.paper_folder || '(not configured)'}
                </p>
                {appSettings.folder_status === 'ok' && (
                  <p className="text-xs text-green-700 mt-1">
                    ✓ Folder accessible · {appSettings.pdf_count} PDF(s) found
                  </p>
                )}
                {appSettings.folder_status === 'not_set' && (
                  <p className="text-xs text-amber-700 mt-1">
                    ⚠ No folder configured.{' '}
                    <Link href="/settings" className="underline">Go to Settings →</Link>
                  </p>
                )}
                {appSettings.folder_status === 'not_found' && (
                  <p className="text-xs text-red-700 mt-1">
                    ✗ Folder not found. Update the path in{' '}
                    <Link href="/settings" className="underline">Settings →</Link>
                  </p>
                )}
              </>
            ) : (
              <p className="text-xs text-gray-400 mt-1">Loading…</p>
            )}
          </div>
        </div>
      </div>

      {/* Quick actions */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <ActionCard
          href="/scan"
          icon={<ScanLine className="w-5 h-5" />}
          title="Scan for PDFs"
          desc="Find new papers and extract data with AI"
          color="blue"
        />
        <ActionCard
          href="/papers"
          icon={<BookOpen className="w-5 h-5" />}
          title="Browse Papers"
          desc="Review extractions, summaries, and raw data"
          color="green"
        />
        <ActionCard
          href="/optimization"
          icon={<TrendingUp className="w-5 h-5" />}
          title="Optimization"
          desc="Bayesian experiment recommendation from literature"
          color="indigo"
        />
        <ActionCard
          href="/settings"
          icon={<Settings className="w-5 h-5" />}
          title="Settings"
          desc="Set paper folder path and configure extraction"
          color="purple"
        />
      </div>

      {/* Last scan errors */}
      {lr && lr.errors.length > 0 && (
        <div className="card p-4">
          <h3 className="font-medium text-red-700 mb-2 flex items-center gap-1.5">
            <AlertTriangle className="w-4 h-4" />
            Last scan errors ({lr.errors.length})
          </h3>
          <ul className="space-y-1">
            {lr.errors.map((e, i) => (
              <li key={i} className="text-xs font-mono text-red-600 bg-red-50 px-2 py-1 rounded truncate">
                {e}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function StatCard({ icon, label, value, sub, bg }: {
  icon: React.ReactNode; label: string; value: string | number;
  sub: string; bg: string;
}) {
  return (
    <div className={`card p-5 flex items-start gap-3 ${bg}`}>
      <div>{icon}</div>
      <div>
        <p className="text-xs text-gray-500 font-medium uppercase tracking-wide">{label}</p>
        <p className="text-2xl font-bold text-gray-900 mt-0.5">{value}</p>
        <p className="text-xs text-gray-500 mt-0.5">{sub}</p>
      </div>
    </div>
  );
}

function ActionCard({ href, icon, title, desc, color }: {
  href: string; icon: React.ReactNode; title: string; desc: string;
  color: 'blue' | 'green' | 'purple' | 'indigo';
}) {
  const colors = {
    blue:   'hover:border-blue-400 hover:bg-blue-50 [&_span]:text-blue-600',
    green:  'hover:border-green-400 hover:bg-green-50 [&_span]:text-green-600',
    purple: 'hover:border-purple-400 hover:bg-purple-50 [&_span]:text-purple-600',
    indigo: 'hover:border-indigo-400 hover:bg-indigo-50 [&_span]:text-indigo-600',
  };
  return (
    <Link href={href} className={`card p-5 flex items-start gap-3 transition-colors cursor-pointer ${colors[color]}`}>
      <span className="mt-0.5">{icon}</span>
      <div>
        <p className="font-semibold text-gray-800">{title}</p>
        <p className="text-xs text-gray-500 mt-0.5">{desc}</p>
      </div>
    </Link>
  );
}
