'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Search, Filter, Download, RefreshCw } from 'lucide-react';
import { papersApi, exportApi } from '@/lib/api';
import { PapersTable } from '@/components/papers/PapersTable';
import type { PaperStatus } from '@/types';
import toast from 'react-hot-toast';

const STATUS_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: 'All statuses' },
  { value: 'uploaded', label: 'Uploaded' },
  { value: 'parsed', label: 'Parsed' },
  { value: 'extracted', label: 'Extracted' },
  { value: 'review_needed', label: 'Review Needed' },
  { value: 'failed', label: 'Failed' },
];

export function PapersListPage() {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [page, setPage] = useState(0);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const limit = 50;

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['papers', search, statusFilter, page],
    queryFn: () =>
      papersApi.list({
        search: search || undefined,
        status: statusFilter || undefined,
        skip: page * limit,
        limit,
        sort_by: 'created_at',
        sort_order: 'desc',
      }),
    refetchInterval: 8000, // auto-refresh for pipeline updates
  });

  const papers = data?.items ?? [];
  const total = data?.total ?? 0;

  const handleExport = async (format: 'csv' | 'json') => {
    try {
      const blob = await exportApi.exportPapers({
        paper_ids: selectedIds.size > 0 ? Array.from(selectedIds) : null,
        format,
        include_raw_extraction: false,
        include_source_evidence: false,
      });
      const ext = format;
      exportApi.downloadFile(blob, `paperlens_export.${ext}`);
      toast.success(`Exported ${selectedIds.size || total} papers as ${format.toUpperCase()}`);
    } catch (err) {
      toast.error('Export failed');
    }
  };

  return (
    <div className="p-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Papers</h1>
          <p className="text-sm text-gray-500 mt-0.5">{total} paper{total !== 1 ? 's' : ''} in database</p>
        </div>
        <div className="flex gap-2">
          {selectedIds.size > 0 && (
            <span className="text-xs text-gray-500 self-center mr-2">
              {selectedIds.size} selected
            </span>
          )}
          <button
            onClick={() => handleExport('csv')}
            className="btn-secondary text-sm flex items-center gap-1.5"
          >
            <Download className="w-3.5 h-3.5" />
            CSV
          </button>
          <button
            onClick={() => handleExport('json')}
            className="btn-secondary text-sm flex items-center gap-1.5"
          >
            <Download className="w-3.5 h-3.5" />
            JSON
          </button>
          <button
            onClick={() => refetch()}
            className="btn-secondary text-sm"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="card p-4 mb-4 flex gap-3 items-center">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            className="input pl-9"
            placeholder="Search title, DOI, filename…"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(0); }}
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-gray-400" />
          <select
            className="input w-auto text-sm"
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(0); }}
          >
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        <PapersTable
          papers={papers}
          selectedIds={selectedIds}
          onSelectionChange={setSelectedIds}
          onRefresh={refetch}
          isLoading={isLoading}
        />
      </div>

      {/* Pagination */}
      {total > limit && (
        <div className="mt-4 flex items-center justify-between text-sm text-gray-500">
          <span>
            Showing {page * limit + 1}–{Math.min((page + 1) * limit, total)} of {total}
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className="btn-secondary"
            >
              Previous
            </button>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={(page + 1) * limit >= total}
              className="btn-secondary"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
