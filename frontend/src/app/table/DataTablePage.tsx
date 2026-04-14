'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Download, Table2, Info } from 'lucide-react';
import { papersApi, exportApi } from '@/lib/api';
import { formatDate, STATUS_COLORS, STATUS_LABELS } from '@/lib/utils';
import type { PaperListItem } from '@/types';
import toast from 'react-hot-toast';
import { cn } from '@/lib/utils';

export function DataTablePage() {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  const { data } = useQuery({
    queryKey: ['papers-table'],
    queryFn: () => papersApi.list({ limit: 200, status: 'extracted' }),
  });

  const papers = data?.items ?? [];

  const toggleSelect = (id: string) => {
    const next = new Set(selectedIds);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelectedIds(next);
  };

  const handleExport = async (format: 'csv' | 'json') => {
    try {
      const blob = await exportApi.exportPapers({
        paper_ids: selectedIds.size > 0 ? Array.from(selectedIds) : null,
        format,
        include_raw_extraction: false,
        include_source_evidence: false,
      });
      exportApi.downloadFile(blob, `paperlens_data.${format}`);
      toast.success('Export downloaded');
    } catch {
      toast.error('Export failed');
    }
  };

  return (
    <div className="p-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Data Table & Export</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Extracted papers ready for analysis · {papers.length} extracted
          </p>
        </div>
        <div className="flex gap-2">
          {selectedIds.size > 0 && (
            <span className="text-xs text-gray-500 self-center">
              {selectedIds.size} selected
            </span>
          )}
          <button
            onClick={() => handleExport('csv')}
            className="btn-primary text-sm flex items-center gap-1.5"
          >
            <Download className="w-3.5 h-3.5" />
            Export CSV
          </button>
          <button
            onClick={() => handleExport('json')}
            className="btn-secondary text-sm flex items-center gap-1.5"
          >
            <Download className="w-3.5 h-3.5" />
            Export JSON
          </button>
        </div>
      </div>

      {/* Info box for BO */}
      <div className="flex gap-3 bg-emerald-50 border border-emerald-100 rounded-lg p-4 mb-5">
        <Info className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
        <div className="text-xs text-emerald-700">
          <p className="font-medium">Bayesian Optimization Ready Export</p>
          <p>The JSON export includes a <code className="font-mono bg-emerald-100 px-1 rounded">bo_ready</code> field
            with explicitly separated <code className="font-mono bg-emerald-100 px-1 rounded">X</code> (input variables) and{' '}
            <code className="font-mono bg-emerald-100 px-1 rounded">y</code> (output variables) for each paper.
            Import directly into scikit-learn, BoTorch, or GPyOpt.
          </p>
        </div>
      </div>

      {papers.length === 0 ? (
        <div className="card p-12 text-center text-gray-400">
          <Table2 className="w-10 h-10 mx-auto mb-3 text-gray-200" />
          <p className="text-sm">No extracted papers yet.</p>
          <p className="text-xs mt-1">
            Ingest PDFs from the{' '}
            <a href="/ingest" className="text-brand-500 hover:underline">Ingest page</a>{' '}
            to see them here.
          </p>
        </div>
      ) : (
        <div className="card overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                <th className="px-3 py-2.5 table-header w-10">
                  <input
                    type="checkbox"
                    className="rounded"
                    checked={selectedIds.size === papers.length}
                    onChange={() => {
                      if (selectedIds.size === papers.length) setSelectedIds(new Set());
                      else setSelectedIds(new Set(papers.map((p) => p.id)));
                    }}
                  />
                </th>
                <th className="px-3 py-2.5 table-header">Title</th>
                <th className="px-3 py-2.5 table-header">Journal</th>
                <th className="px-3 py-2.5 table-header">Year</th>
                <th className="px-3 py-2.5 table-header">Status</th>
                <th className="px-3 py-2.5 table-header">Extraction</th>
                <th className="px-3 py-2.5 table-header">Review</th>
                <th className="px-3 py-2.5 table-header">Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {papers.map((paper) => (
                <tr
                  key={paper.id}
                  className={cn(
                    'hover:bg-gray-50 transition-colors',
                    selectedIds.has(paper.id) && 'bg-brand-50'
                  )}
                >
                  <td className="px-3 py-2.5">
                    <input
                      type="checkbox"
                      className="rounded"
                      checked={selectedIds.has(paper.id)}
                      onChange={() => toggleSelect(paper.id)}
                    />
                  </td>
                  <td className="px-3 py-2.5">
                    <a
                      href={`/papers/${paper.id}`}
                      className="text-brand-600 hover:underline font-medium"
                    >
                      {paper.title || paper.original_filename}
                    </a>
                  </td>
                  <td className="px-3 py-2.5 text-xs text-gray-600">
                    {paper.journal_name || '–'}
                  </td>
                  <td className="px-3 py-2.5 text-xs text-gray-600 tabular-nums">
                    {paper.publication_year || '–'}
                  </td>
                  <td className="px-3 py-2.5">
                    <span className={cn('badge', STATUS_COLORS[paper.status])}>
                      {STATUS_LABELS[paper.status]}
                    </span>
                  </td>
                  <td className="px-3 py-2.5">
                    {paper.has_extraction ? (
                      <span className="badge bg-green-100 text-green-700 border-green-200">✓</span>
                    ) : (
                      <span className="text-xs text-gray-400">–</span>
                    )}
                  </td>
                  <td className="px-3 py-2.5">
                    {paper.needs_review ? (
                      <span className="badge bg-amber-100 text-amber-700 border-amber-200">⚠</span>
                    ) : (
                      <span className="text-xs text-gray-400">–</span>
                    )}
                  </td>
                  <td className="px-3 py-2.5 text-xs text-gray-500">
                    {formatDate(paper.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
