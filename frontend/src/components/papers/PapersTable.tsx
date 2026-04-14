'use client';

import { useState, useMemo } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
} from '@tanstack/react-table';
import {
  ChevronUp, ChevronDown, ChevronsUpDown, ExternalLink,
  Download, RotateCcw, Trash2, Eye,
} from 'lucide-react';
import Link from 'next/link';
import { cn, formatDate, formatBytes, truncate, STATUS_COLORS, STATUS_LABELS } from '@/lib/utils';
import type { PaperListItem, PaperStatus } from '@/types';
import { papersApi } from '@/lib/api';
import toast from 'react-hot-toast';

interface PapersTableProps {
  papers: PaperListItem[];
  selectedIds: Set<string>;
  onSelectionChange: (ids: Set<string>) => void;
  onRefresh: () => void;
  isLoading?: boolean;
}

export function PapersTable({
  papers,
  selectedIds,
  onSelectionChange,
  onRefresh,
  isLoading,
}: PapersTableProps) {
  const [sorting, setSorting] = useState<SortingState>([]);

  const toggleSelect = (id: string) => {
    const next = new Set(selectedIds);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    onSelectionChange(next);
  };

  const toggleAll = () => {
    if (selectedIds.size === papers.length) {
      onSelectionChange(new Set());
    } else {
      onSelectionChange(new Set(papers.map((p) => p.id)));
    }
  };

  const handleReprocess = async (paperId: string) => {
    try {
      await papersApi.reprocess(paperId, 'full');
      toast.success('Reprocessing queued');
      onRefresh();
    } catch {
      toast.error('Failed to queue reprocessing');
    }
  };

  const handleDelete = async (paperId: string, filename: string) => {
    if (!confirm(`Delete "${filename}"? This cannot be undone.`)) return;
    try {
      await papersApi.delete(paperId);
      toast.success('Paper deleted');
      onRefresh();
    } catch {
      toast.error('Failed to delete paper');
    }
  };

  const columns = useMemo<ColumnDef<PaperListItem>[]>(
    () => [
      {
        id: 'select',
        header: () => (
          <input
            type="checkbox"
            className="rounded border-gray-300"
            checked={selectedIds.size === papers.length && papers.length > 0}
            onChange={toggleAll}
          />
        ),
        cell: ({ row }) => (
          <input
            type="checkbox"
            className="rounded border-gray-300"
            checked={selectedIds.has(row.original.id)}
            onChange={() => toggleSelect(row.original.id)}
          />
        ),
        size: 40,
      },
      {
        accessorKey: 'title',
        header: 'Title / File',
        cell: ({ row }) => (
          <div className="max-w-xs">
            <Link
              href={`/papers/${row.original.id}`}
              className="text-sm font-medium text-brand-600 hover:text-brand-700 hover:underline block truncate"
              title={row.original.title || row.original.original_filename}
            >
              {row.original.title || row.original.original_filename}
            </Link>
            {row.original.title && (
              <p className="text-xs text-gray-400 truncate mt-0.5">
                {row.original.original_filename}
              </p>
            )}
          </div>
        ),
      },
      {
        accessorKey: 'author_names',
        header: 'Authors',
        cell: ({ row }) => (
          <span className="text-xs text-gray-600">
            {row.original.author_names?.length
              ? truncate(row.original.author_names.join(', '), 40)
              : '–'}
          </span>
        ),
      },
      {
        accessorKey: 'journal_name',
        header: 'Journal',
        cell: ({ getValue }) => (
          <span className="text-xs text-gray-600">{(getValue() as string) || '–'}</span>
        ),
      },
      {
        accessorKey: 'publication_year',
        header: 'Year',
        cell: ({ getValue }) => (
          <span className="text-xs text-gray-600">{(getValue() as number) || '–'}</span>
        ),
      },
      {
        accessorKey: 'status',
        header: 'Status',
        cell: ({ getValue }) => {
          const status = getValue() as PaperStatus;
          return (
            <span className={cn('badge', STATUS_COLORS[status])}>
              {STATUS_LABELS[status]}
            </span>
          );
        },
      },
      {
        id: 'extraction',
        header: 'Extraction',
        cell: ({ row }) => {
          const { has_extraction, needs_review } = row.original;
          if (!has_extraction) return <span className="text-xs text-gray-400">–</span>;
          if (needs_review)
            return <span className="badge bg-amber-100 text-amber-700 border-amber-200">Review</span>;
          return <span className="badge bg-green-100 text-green-700 border-green-200">Done</span>;
        },
      },
      {
        accessorKey: 'page_count',
        header: 'Pages',
        cell: ({ getValue }) => (
          <span className="text-xs text-gray-500 tabular-nums">{(getValue() as number) || '–'}</span>
        ),
      },
      {
        accessorKey: 'created_at',
        header: 'Uploaded',
        cell: ({ getValue }) => (
          <span className="text-xs text-gray-500">{formatDate(getValue() as string)}</span>
        ),
      },
      {
        id: 'actions',
        header: '',
        cell: ({ row }) => (
          <div className="flex items-center gap-1">
            <Link href={`/papers/${row.original.id}`} className="p-1.5 text-gray-400 hover:text-brand-600 rounded">
              <Eye className="w-3.5 h-3.5" />
            </Link>
            {row.original.has_extraction && (
              <a
                href={papersApi.downloadSummary(row.original.id)}
                className="p-1.5 text-gray-400 hover:text-green-600 rounded"
                title="Download summary"
                download
              >
                <Download className="w-3.5 h-3.5" />
              </a>
            )}
            <button
              onClick={() => handleReprocess(row.original.id)}
              className="p-1.5 text-gray-400 hover:text-blue-600 rounded"
              title="Reprocess"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => handleDelete(row.original.id, row.original.original_filename)}
              className="p-1.5 text-gray-400 hover:text-red-600 rounded"
              title="Delete"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        ),
      },
    ],
    [selectedIds, papers]
  );

  const table = useReactTable({
    data: papers,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  if (isLoading) {
    return (
      <div className="p-12 text-center text-gray-400 text-sm">
        Loading papers…
      </div>
    );
  }

  if (!papers.length) {
    return (
      <div className="p-12 text-center text-gray-400">
        <p className="text-sm">No papers found.</p>
        <Link href="/upload" className="text-brand-500 hover:underline text-sm mt-1 inline-block">
          Upload your first paper →
        </Link>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          {table.getHeaderGroups().map((headerGroup) => (
            <tr key={headerGroup.id} className="border-b border-gray-100 bg-gray-50">
              {headerGroup.headers.map((header) => (
                <th
                  key={header.id}
                  className="px-3 py-2.5 table-header"
                  style={{ width: header.getSize() }}
                >
                  {header.isPlaceholder ? null : (
                    <div
                      className={cn(
                        'flex items-center gap-1',
                        header.column.getCanSort() && 'cursor-pointer select-none'
                      )}
                      onClick={header.column.getToggleSortingHandler()}
                    >
                      {flexRender(header.column.columnDef.header, header.getContext())}
                      {header.column.getCanSort() && (
                        <span className="text-gray-300">
                          {header.column.getIsSorted() === 'asc' ? (
                            <ChevronUp className="w-3 h-3" />
                          ) : header.column.getIsSorted() === 'desc' ? (
                            <ChevronDown className="w-3 h-3" />
                          ) : (
                            <ChevronsUpDown className="w-3 h-3" />
                          )}
                        </span>
                      )}
                    </div>
                  )}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody className="divide-y divide-gray-100">
          {table.getRowModel().rows.map((row) => (
            <tr
              key={row.id}
              className={cn(
                'hover:bg-gray-50 transition-colors',
                selectedIds.has(row.original.id) && 'bg-brand-50'
              )}
            >
              {row.getVisibleCells().map((cell) => (
                <td key={cell.id} className="px-3 py-2.5 align-middle">
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
