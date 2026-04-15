'use client';

import { useQuery } from '@tanstack/react-query';
import { papersApi, ingestApi } from '@/lib/api';
import {
  BookOpen, CheckCircle, AlertTriangle, XCircle,
  FolderInput, ArrowRight, Clock, FolderOpen,
} from 'lucide-react';
import Link from 'next/link';
import { formatDate } from '@/lib/utils';
import { StatusBadge } from '@/components/ui/StatusBadge';
import type { PaperStatus } from '@/types';

export function DashboardPage() {
  const { data } = useQuery({
    queryKey: ['papers-summary'],
    queryFn: () => papersApi.list({ limit: 200 }),
    refetchInterval: 5000, // poll for pipeline updates
  });

  const { data: ingestStatus } = useQuery({
    queryKey: ['ingest-status'],
    queryFn: ingestApi.getStatus,
    refetchInterval: 30_000,
  });

  const papers = data?.items ?? [];
  const total = data?.total ?? 0;

  // Compute status counts
  const counts: Record<PaperStatus, number> = {
    uploaded: 0, parsing: 0, parsed: 0, extracting: 0,
    extracted: 0, review_needed: 0, failed: 0,
  };
  papers.forEach((p) => {
    counts[p.status] = (counts[p.status] || 0) + 1;
  });

  const stats = [
    {
      label: 'Total Papers',
      value: total,
      icon: BookOpen,
      color: 'text-blue-600',
      bg: 'bg-blue-50',
    },
    {
      label: 'Extracted',
      value: counts.extracted,
      icon: CheckCircle,
      color: 'text-green-600',
      bg: 'bg-green-50',
    },
    {
      label: 'Needs Review',
      value: counts.review_needed,
      icon: AlertTriangle,
      color: 'text-amber-600',
      bg: 'bg-amber-50',
    },
    {
      label: 'Failed',
      value: counts.failed,
      icon: XCircle,
      color: 'text-red-600',
      bg: 'bg-red-50',
    },
  ];

  const inProgress = papers.filter((p) =>
    ['parsing', 'extracting'].includes(p.status)
  );

  const recentPapers = papers
    .sort((a, b) => b.created_at.localeCompare(a.created_at))
    .slice(0, 8);

  return (
    <div className="p-8 max-w-6xl">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-gray-900">Dashboard</h1>
        <p className="text-sm text-gray-500 mt-1">
          Scientific paper extraction pipeline · real-time status
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        {stats.map((stat) => (
          <div key={stat.label} className="card p-5">
            <div className="flex items-center gap-3">
              <div className={`w-9 h-9 rounded-lg ${stat.bg} flex items-center justify-center`}>
                <stat.icon className={`w-5 h-5 ${stat.color}`} />
              </div>
              <div>
                <div className="text-2xl font-bold text-gray-900 tabular-nums">{stat.value}</div>
                <div className="text-xs text-gray-500">{stat.label}</div>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* In Progress + Folder status */}
        <div className="col-span-1 space-y-4">
          {/* Ingestion folder */}
          <div className="card p-5">
            <div className="flex items-center gap-2 mb-3">
              <FolderOpen className="w-4 h-4 text-gray-400" />
              <h3 className="font-medium text-gray-700 text-sm">Ingestion Folder</h3>
            </div>
            {ingestStatus ? (
              <>
                <p className="text-xs font-mono text-gray-500 truncate mb-1">
                  {ingestStatus.ingest_dir}
                </p>
                <div className="flex items-center gap-1.5">
                  {ingestStatus.mounted ? (
                    <span className="badge bg-green-100 text-green-700 border-green-200 text-xs">
                      ✓ Mounted
                    </span>
                  ) : (
                    <span className="badge bg-amber-100 text-amber-700 border-amber-200 text-xs">
                      ⚠ Not mounted
                    </span>
                  )}
                  {ingestStatus.pdf_count_in_folder !== null && (
                    <span className="text-xs text-gray-500">
                      {ingestStatus.pdf_count_in_folder} PDF{ingestStatus.pdf_count_in_folder !== 1 ? 's' : ''}
                    </span>
                  )}
                </div>
              </>
            ) : (
              <p className="text-xs text-gray-400">Loading…</p>
            )}
            <div className="mt-3 pt-3 border-t border-gray-100">
              <Link
                href="/ingest"
                className="flex items-center gap-2 text-sm text-brand-600 hover:text-brand-700"
              >
                <FolderInput className="w-4 h-4" />
                Scan for new PDFs
              </Link>
            </div>
          </div>

          {/* In Progress */}
          <div className="card p-5">
            <div className="flex items-center gap-2 mb-4">
              <Clock className="w-4 h-4 text-purple-500" />
              <h3 className="font-medium text-gray-700">Processing</h3>
              {inProgress.length > 0 && (
                <span className="badge bg-purple-100 text-purple-700 border-purple-200 ml-auto">
                  {inProgress.length} active
                </span>
              )}
            </div>
            {inProgress.length === 0 ? (
              <p className="text-xs text-gray-400">No papers currently processing</p>
            ) : (
              <div className="space-y-2">
                {inProgress.map((p) => (
                  <div key={p.id} className="flex items-center gap-2">
                    <StatusBadge status={p.status} />
                    <span className="text-xs text-gray-600 truncate flex-1">
                      {p.title || p.original_filename}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Recent Papers */}
        <div className="col-span-2 card">
          <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
            <h3 className="font-medium text-gray-700">Recent Papers</h3>
            <Link href="/papers" className="text-xs text-brand-500 hover:text-brand-600 flex items-center gap-1">
              View all <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
          <div className="divide-y divide-gray-100">
            {recentPapers.length === 0 ? (
              <div className="p-8 text-center text-sm text-gray-400">
                No papers yet.{' '}
                <Link href="/ingest" className="text-brand-500 hover:underline">
                  Scan your folder to ingest PDFs →
                </Link>
              </div>
            ) : (
              recentPapers.map((paper) => (
                <Link
                  key={paper.id}
                  href={`/papers/${paper.id}`}
                  className="flex items-center gap-4 px-5 py-3 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-800 truncate">
                      {paper.title || paper.original_filename}
                    </p>
                    <p className="text-xs text-gray-400 mt-0.5">
                      {paper.author_names?.[0] || '–'} · {paper.publication_year || '–'} · {formatDate(paper.created_at)}
                    </p>
                  </div>
                  <StatusBadge status={paper.status} />
                </Link>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Quick links */}
      <div className="mt-6 card p-5">
        <h3 className="font-medium text-gray-700 mb-3">Quick Actions</h3>
        <div className="flex gap-3">
          <Link href="/ingest" className="btn-primary text-sm flex items-center gap-1.5">
            <FolderInput className="w-4 h-4" />
            Scan for PDFs
          </Link>
          <Link href="/papers" className="btn-secondary text-sm">
            Browse Papers
          </Link>
          <Link href="/table" className="btn-secondary text-sm">
            Data Table &amp; Export
          </Link>
        </div>
      </div>
    </div>
  );
}
