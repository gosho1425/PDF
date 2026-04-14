'use client';

import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, FileText, X, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { cn, formatBytes } from '@/lib/utils';
import { papersApi } from '@/lib/api';
import type { UploadResult } from '@/types';
import toast from 'react-hot-toast';

interface FileWithStatus {
  file: File;
  status: 'pending' | 'uploading' | 'queued' | 'failed' | 'duplicate';
  result?: UploadResult;
  error?: string;
}

interface UploadZoneProps {
  onUploadComplete?: () => void;
}

export function UploadZone({ onUploadComplete }: UploadZoneProps) {
  const [files, setFiles] = useState<FileWithStatus[]>([]);
  const [isUploading, setIsUploading] = useState(false);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const newFiles = acceptedFiles.map((file) => ({
      file,
      status: 'pending' as const,
    }));
    setFiles((prev) => [...prev, ...newFiles]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    multiple: true,
    maxSize: 100 * 1024 * 1024, // 100 MB
  });

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const uploadAll = async () => {
    const pendingFiles = files.filter((f) => f.status === 'pending');
    if (!pendingFiles.length) return;

    setIsUploading(true);
    setFiles((prev) =>
      prev.map((f) => (f.status === 'pending' ? { ...f, status: 'uploading' } : f))
    );

    try {
      const results = await papersApi.upload(pendingFiles.map((f) => f.file));

      setFiles((prev) =>
        prev.map((fileWithStatus) => {
          const result = results.find((r) => r.filename === fileWithStatus.file.name);
          if (!result) return fileWithStatus;
          return {
            ...fileWithStatus,
            status:
              result.status === 'queued'
                ? 'queued'
                : result.status === 'failed' || result.status === 'rejected'
                ? 'failed'
                : 'queued',
            result,
            error: result.error,
          };
        })
      );

      const queued = results.filter((r) => r.status === 'queued').length;
      const failed = results.filter((r) => r.status === 'failed' || r.status === 'rejected').length;

      if (queued > 0) toast.success(`${queued} paper(s) queued for processing`);
      if (failed > 0) toast.error(`${failed} file(s) failed to upload`);

      onUploadComplete?.();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Upload failed');
      setFiles((prev) =>
        prev.map((f) => (f.status === 'uploading' ? { ...f, status: 'failed' } : f))
      );
    } finally {
      setIsUploading(false);
    }
  };

  const pendingCount = files.filter((f) => f.status === 'pending').length;

  return (
    <div className="space-y-4">
      {/* Drop zone */}
      <div
        {...getRootProps()}
        className={cn(
          'border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors',
          isDragActive
            ? 'border-brand-500 bg-brand-50'
            : 'border-gray-200 hover:border-brand-300 hover:bg-gray-50'
        )}
      >
        <input {...getInputProps()} />
        <Upload className="w-10 h-10 text-gray-300 mx-auto mb-3" />
        <p className="text-sm font-medium text-gray-600">
          {isDragActive ? 'Drop PDF files here…' : 'Drag & drop PDF files, or click to select'}
        </p>
        <p className="text-xs text-gray-400 mt-1">Multiple files supported · Max 100 MB per file</p>
      </div>

      {/* File list */}
      {files.length > 0 && (
        <div className="space-y-2">
          {files.map((fileWithStatus, index) => (
            <div
              key={`${fileWithStatus.file.name}-${index}`}
              className="flex items-center gap-3 p-3 bg-white border border-gray-200 rounded-lg"
            >
              <FileText className="w-4 h-4 text-gray-400 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-800 truncate">
                  {fileWithStatus.file.name}
                </p>
                <p className="text-xs text-gray-400">{formatBytes(fileWithStatus.file.size)}</p>
                {fileWithStatus.error && (
                  <p className="text-xs text-red-500 mt-0.5">{fileWithStatus.error}</p>
                )}
                {fileWithStatus.result?.message && (
                  <p className="text-xs text-amber-600 mt-0.5">{fileWithStatus.result.message}</p>
                )}
              </div>
              <div className="flex-shrink-0">
                {fileWithStatus.status === 'pending' && (
                  <button onClick={() => removeFile(index)} className="text-gray-300 hover:text-red-400">
                    <X className="w-4 h-4" />
                  </button>
                )}
                {fileWithStatus.status === 'uploading' && (
                  <Loader2 className="w-4 h-4 text-brand-500 animate-spin" />
                )}
                {fileWithStatus.status === 'queued' && (
                  <CheckCircle className="w-4 h-4 text-green-500" />
                )}
                {fileWithStatus.status === 'failed' && (
                  <AlertCircle className="w-4 h-4 text-red-500" />
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Actions */}
      {pendingCount > 0 && (
        <button onClick={uploadAll} disabled={isUploading} className="btn-primary w-full">
          {isUploading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin mr-2 inline" />
              Uploading…
            </>
          ) : (
            `Upload ${pendingCount} file${pendingCount > 1 ? 's' : ''}`
          )}
        </button>
      )}
    </div>
  );
}
