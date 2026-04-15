'use client';

import { useEffect, useState, useCallback } from 'react';
import { papersApi } from '@/lib/api';
import type { Paper, PaperList } from '@/types';
import { StatusBadge } from '@/components/ui/StatusBadge';
import toast from 'react-hot-toast';
import {
  Search, RefreshCw, ChevronLeft, ChevronRight,
  Eye, RotateCcw, Trash2
} from 'lucide-react';
import Link from 'next/link';

const PAGE_SIZE = 25;

export default function PapersPage() {
  const [data, setData] = useState<PaperList | null>(null);
  const [page, setPage] = useState(0);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await papersApi.list({
        skip: page * PAGE_SIZE,
        limit: PAGE_SIZE,
        search: search || undefined,
        status: statusFilter || undefined,
        sort_by: 'created_at',
        sort_order: 'desc',
      });
      setData(r);
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
  }, [page, search, statusFilter]);

  useEffect(() => { load(); }, [load]);

  const reprocess = async (id: string, name: string) => {
    if (!confirm(`Re-extract "${name}"? This will call the LLM again.`)) return;
    try {
      await papersApi.reprocess(id);
      toast.success('Re-processing started');
      load();
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const deletePaper = async (id: string, name: string) => {
    if (!confirm(`Delete "${name}"? This cannot be undone.`)) return;
    try {
      await papersApi.delete(id);
      toast.success('Paper deleted');
      load();
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Papers</h1>
          <p className="text-gray-500 mt-1">
            {data?.total ?? '…'} papers in database
          </p>
        </div>
        <button onClick={load} disabled={loading} className="btn-secondary text-sm">
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-2 flex-wrap">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-2.5 w-4 h-4 text-gray-400" />
          <input
            className="input pl-9"
            placeholder="Search title, filename, journal…"
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(0); }}
          />
        </div>
        <select
          className="input w-40"
          value={statusFilter}
          onChange={e => { setStatusFilter(e.target.value); setPage(0); }}
        >
          <option value="">All statuses</option>
          <option value="done">Done</option>
          <option value="failed">Failed</option>
          <option value="processing">Processing</option>
          <option value="pending">Pending</option>
        </select>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-gray-400">Loading…</div>
        ) : !data?.items.length ? (
          <div className="p-8 text-center text-gray-400">
            <p className="font-medium">No papers found</p>
            <p className="text-sm mt-1">Run a scan to import PDFs from your folder.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50">
                  <th className="px-4 py-3 text-left font-medium text-gray-500">Paper</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">Journal / Year</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">Status</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">Processed</th>
                  <th className="px-4 py-3 text-right font-medium text-gray-500">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {data.items.map(paper => (
                  <PaperRow
                    key={paper.id}
                    paper={paper}
                    onReprocess={reprocess}
                    onDelete={deletePaper}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between text-sm text-gray-500">
          <span>
            Showing {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, data?.total ?? 0)} of {data?.total}
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => setPage(p => Math.max(0, p - 1))}
              disabled={page === 0}
              className="btn-secondary"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="px-3 py-1.5 text-sm">{page + 1} / {totalPages}</span>
            <button
              onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1}
              className="btn-secondary"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function PaperRow({ paper, onReprocess, onDelete }: {
  paper: Paper;
  onReprocess: (id: string, name: string) => void;
  onDelete: (id: string, name: string) => void;
}) {
  const displayTitle = paper.title || paper.file_name;
  const authors = paper.authors?.slice(0, 2).join(', ') +
    (paper.authors?.length > 2 ? ' et al.' : '');

  return (
    <tr className="hover:bg-gray-50 transition-colors">
      <td className="px-4 py-3">
        <p className="font-medium text-gray-900 truncate max-w-sm" title={displayTitle}>
          {displayTitle}
        </p>
        {authors && (
          <p className="text-xs text-gray-400 mt-0.5 truncate max-w-sm">{authors}</p>
        )}
        <p className="text-xs text-gray-300 font-mono mt-0.5 truncate max-w-sm">
          {paper.file_name}
        </p>
      </td>
      <td className="px-4 py-3 whitespace-nowrap">
        <p className="text-gray-700">{paper.journal || '—'}</p>
        <p className="text-xs text-gray-400">{paper.year || ''}</p>
      </td>
      <td className="px-4 py-3">
        <StatusBadge status={paper.status} />
        {paper.status === 'failed' && paper.error_message && (
          <p className="text-xs text-red-500 mt-1 truncate max-w-[200px]" title={paper.error_message}>
            {paper.error_message}
          </p>
        )}
      </td>
      <td className="px-4 py-3 whitespace-nowrap text-xs text-gray-400">
        {paper.processed_at
          ? new Date(paper.processed_at).toLocaleDateString('en-GB')
          : '—'}
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center justify-end gap-1">
          {paper.has_extraction && (
            <Link
              href={`/papers/${paper.id}`}
              className="p-1.5 rounded hover:bg-gray-100 text-gray-500 hover:text-blue-600"
              title="View extraction"
            >
              <Eye className="w-4 h-4" />
            </Link>
          )}
          <button
            onClick={() => onReprocess(paper.id, paper.file_name)}
            className="p-1.5 rounded hover:bg-gray-100 text-gray-500 hover:text-amber-600"
            title="Re-extract"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
          <button
            onClick={() => onDelete(paper.id, paper.file_name)}
            className="p-1.5 rounded hover:bg-gray-100 text-gray-500 hover:text-red-600"
            title="Delete"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </td>
    </tr>
  );
}
