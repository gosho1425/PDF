'use client';

import { useQuery } from '@tanstack/react-query';
import {
  ArrowLeft, Download, RotateCcw, FileText, Hash,
  Calendar, BookOpen, Users, FileDigit,
} from 'lucide-react';
import Link from 'next/link';
import { papersApi } from '@/lib/api';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { ExtractionPanel } from '@/components/papers/ExtractionPanel';
import { formatBytes, formatDate, truncate } from '@/lib/utils';
import toast from 'react-hot-toast';

interface PaperDetailContentProps {
  paperId: string;
}

function MetaItem({ icon: Icon, label, value }: {
  icon: React.ElementType;
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="flex items-start gap-3 py-2 border-b border-gray-100 last:border-0">
      <Icon className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" />
      <div>
        <div className="text-xs text-gray-500 font-medium">{label}</div>
        <div className="text-sm text-gray-800 mt-0.5">{value || '–'}</div>
      </div>
    </div>
  );
}

export function PaperDetailContent({ paperId }: PaperDetailContentProps) {
  const { data: paper, isLoading, error, refetch } = useQuery({
    queryKey: ['paper', paperId],
    queryFn: () => papersApi.get(paperId),
    refetchInterval: (data) => {
      const status = data?.state?.data?.status;
      return status && ['parsing', 'extracting'].includes(status) ? 3000 : false;
    },
  });

  const handleReprocess = async (stage: 'full' | 'parse' | 'extract') => {
    try {
      await papersApi.reprocess(paperId, stage);
      toast.success(`${stage} queued`);
      setTimeout(() => refetch(), 1000);
    } catch {
      toast.error('Failed to queue reprocessing');
    }
  };

  if (isLoading) {
    return (
      <div className="p-8">
        <div className="h-6 bg-gray-100 rounded w-64 animate-pulse" />
        <div className="h-4 bg-gray-100 rounded w-40 mt-2 animate-pulse" />
      </div>
    );
  }

  if (error || !paper) {
    return (
      <div className="p-8">
        <p className="text-red-500">Paper not found.</p>
        <Link href="/papers" className="text-brand-500 hover:underline mt-2 inline-block">
          ← Back to papers
        </Link>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-6xl">
      {/* Breadcrumb */}
      <Link
        href="/papers"
        className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 mb-6"
      >
        <ArrowLeft className="w-4 h-4" />
        Papers
      </Link>

      {/* Header */}
      <div className="flex items-start justify-between gap-4 mb-6">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <StatusBadge status={paper.status} />
            {paper.parse_method && (
              <span className="badge bg-gray-100 text-gray-600 border-gray-200">
                {paper.parse_method} parse
              </span>
            )}
          </div>
          <h1 className="text-xl font-semibold text-gray-900 leading-tight">
            {paper.title || paper.original_filename}
          </h1>
          {paper.title && (
            <p className="text-sm text-gray-400 mt-1">{paper.original_filename}</p>
          )}
          {paper.doi && (
            <a
              href={`https://doi.org/${paper.doi}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-brand-500 hover:underline mt-1 inline-block font-mono"
            >
              DOI: {paper.doi}
            </a>
          )}
        </div>

        {/* Actions */}
        <div className="flex flex-col gap-2 flex-shrink-0">
          {paper.summary_available && (
            <a
              href={papersApi.downloadSummary(paperId)}
              className="btn-secondary text-sm flex items-center gap-1.5"
              download
            >
              <Download className="w-3.5 h-3.5" />
              Summary.md
            </a>
          )}
          {paper.extraction_available && (
            <a
              href={papersApi.downloadExtractionJson(paperId)}
              className="btn-secondary text-sm flex items-center gap-1.5"
              download
            >
              <Download className="w-3.5 h-3.5" />
              extraction.json
            </a>
          )}
          <button
            onClick={() => handleReprocess('full')}
            className="btn-secondary text-sm flex items-center gap-1.5"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Reprocess
          </button>
        </div>
      </div>

      {/* Error display */}
      {(paper.parse_error || paper.extraction_error) && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-sm font-medium text-red-700 mb-1">Processing Error</p>
          <p className="text-xs text-red-600 font-mono">
            {paper.parse_error || paper.extraction_error}
          </p>
        </div>
      )}

      <div className="grid grid-cols-3 gap-6">
        {/* Left: Metadata */}
        <div className="col-span-1 space-y-4">
          <div className="card p-4">
            <h2 className="font-medium text-gray-700 mb-3 text-sm">Bibliographic Info</h2>
            <MetaItem
              icon={BookOpen}
              label="Journal"
              value={paper.journal?.name}
            />
            <MetaItem
              icon={Users}
              label="Authors"
              value={
                paper.authors?.length
                  ? paper.authors.map((a) => a.name).join(', ')
                  : undefined
              }
            />
            <MetaItem
              icon={Calendar}
              label="Year"
              value={paper.publication_year?.toString()}
            />
            {paper.volume && (
              <MetaItem
                icon={FileDigit}
                label="Volume/Issue/Pages"
                value={`${paper.volume}/${paper.issue || '–'}/${paper.pages || '–'}`}
              />
            )}
            {paper.keywords && paper.keywords.length > 0 && (
              <div className="py-2">
                <p className="text-xs text-gray-500 font-medium mb-1.5">Keywords</p>
                <div className="flex flex-wrap gap-1">
                  {paper.keywords.map((kw, i) => (
                    <span key={i} className="badge bg-gray-100 text-gray-600 border-gray-200 text-[10px]">
                      {kw}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="card p-4">
            <h2 className="font-medium text-gray-700 mb-3 text-sm">File Info</h2>
            <MetaItem icon={FileText} label="Filename" value={paper.original_filename} />
            <MetaItem icon={FileDigit} label="Pages" value={paper.page_count?.toString()} />
            <MetaItem icon={FileDigit} label="Size" value={formatBytes(paper.file_size_bytes)} />
            <MetaItem icon={Calendar} label="Uploaded" value={formatDate(paper.created_at)} />
            {paper.file_hash_sha256 && (
              <div className="py-2">
                <p className="text-xs text-gray-500 font-medium mb-1">SHA-256</p>
                <p className="text-[10px] font-mono text-gray-400 break-all">
                  {paper.file_hash_sha256}
                </p>
              </div>
            )}
          </div>

          {paper.abstract && (
            <div className="card p-4">
              <h2 className="font-medium text-gray-700 mb-2 text-sm">Abstract</h2>
              <p className="text-xs text-gray-600 leading-relaxed">{paper.abstract}</p>
            </div>
          )}
        </div>

        {/* Right: Extraction */}
        <div className="col-span-2">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-medium text-gray-700">Extracted Data</h2>
            <div className="flex gap-2">
              <button
                onClick={() => handleReprocess('extract')}
                className="text-xs text-gray-500 hover:text-brand-600 flex items-center gap-1"
              >
                <RotateCcw className="w-3 h-3" />
                Re-extract
              </button>
            </div>
          </div>
          <ExtractionPanel paperId={paperId} />
        </div>
      </div>
    </div>
  );
}
