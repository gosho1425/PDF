import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import type { PaperStatus, ExtractionStatus } from '@/types';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatBytes(bytes: number | null): string {
  if (!bytes) return '–';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatDate(dateString: string): string {
  try {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return dateString;
  }
}

export const STATUS_COLORS: Record<PaperStatus, string> = {
  uploaded: 'bg-gray-100 text-gray-700 border-gray-200',
  parsing: 'bg-blue-100 text-blue-700 border-blue-200 animate-pulse',
  parsed: 'bg-sky-100 text-sky-700 border-sky-200',
  extracting: 'bg-purple-100 text-purple-700 border-purple-200 animate-pulse',
  extracted: 'bg-green-100 text-green-700 border-green-200',
  review_needed: 'bg-amber-100 text-amber-700 border-amber-200',
  failed: 'bg-red-100 text-red-700 border-red-200',
};

export const STATUS_LABELS: Record<PaperStatus, string> = {
  uploaded: 'Uploaded',
  parsing: 'Parsing…',
  parsed: 'Parsed',
  extracting: 'Extracting…',
  extracted: 'Extracted',
  review_needed: 'Review Needed',
  failed: 'Failed',
};

export const EXTRACTION_STATUS_COLORS: Record<ExtractionStatus, string> = {
  pending: 'bg-gray-100 text-gray-700',
  complete: 'bg-green-100 text-green-700',
  partial: 'bg-yellow-100 text-yellow-700',
  failed: 'bg-red-100 text-red-700',
  needs_review: 'bg-amber-100 text-amber-700',
};

export function confidenceColor(confidence: number | null): string {
  if (confidence === null) return 'text-gray-400';
  if (confidence >= 0.9) return 'text-green-600';
  if (confidence >= 0.7) return 'text-yellow-600';
  return 'text-red-600';
}

export function confidenceLabel(confidence: number | null): string {
  if (confidence === null) return 'unknown';
  if (confidence >= 0.9) return 'high';
  if (confidence >= 0.7) return 'medium';
  return 'low';
}

export function truncate(str: string | null, maxLen: number): string {
  if (!str) return '–';
  if (str.length <= maxLen) return str;
  return str.slice(0, maxLen) + '…';
}
