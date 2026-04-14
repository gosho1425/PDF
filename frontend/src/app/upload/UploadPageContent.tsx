'use client';

import { useState } from 'react';
import { Upload, FolderOpen, Info } from 'lucide-react';
import { UploadZone } from '@/components/papers/UploadZone';
import { papersApi } from '@/lib/api';
import toast from 'react-hot-toast';

export function UploadPageContent() {
  const [folderPath, setFolderPath] = useState('');
  const [scanning, setScanning] = useState(false);

  const handleFolderScan = async () => {
    if (!folderPath.trim()) return;
    setScanning(true);
    try {
      const result = await papersApi.scanFolder(folderPath.trim());
      toast.success(`Folder scan started (task: ${result.task_id})`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Scan failed');
    } finally {
      setScanning(false);
    }
  };

  return (
    <div className="p-8 max-w-3xl">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-gray-900">Upload Papers</h1>
        <p className="text-sm text-gray-500 mt-1">
          Upload PDF files for automated parsing and LLM-based scientific extraction.
        </p>
      </div>

      <div className="space-y-6">
        {/* File upload */}
        <div className="card p-6">
          <div className="flex items-center gap-2 mb-4">
            <Upload className="w-4 h-4 text-brand-600" />
            <h2 className="font-medium text-gray-700">Direct Upload</h2>
          </div>
          <UploadZone />
        </div>

        {/* Folder scan */}
        <div className="card p-6">
          <div className="flex items-center gap-2 mb-4">
            <FolderOpen className="w-4 h-4 text-brand-600" />
            <h2 className="font-medium text-gray-700">Scan Local Folder</h2>
          </div>
          <p className="text-xs text-gray-500 mb-4">
            Scan a folder on the server filesystem for PDF files and queue them all for processing.
            Useful for batch ingestion from your existing paper collection.
          </p>
          <div className="flex gap-3">
            <input
              type="text"
              className="input flex-1"
              placeholder="/path/to/papers/folder"
              value={folderPath}
              onChange={(e) => setFolderPath(e.target.value)}
            />
            <button
              onClick={handleFolderScan}
              disabled={!folderPath.trim() || scanning}
              className="btn-primary"
            >
              {scanning ? 'Scanning…' : 'Scan Folder'}
            </button>
          </div>
        </div>

        {/* Info box */}
        <div className="flex gap-3 bg-blue-50 border border-blue-100 rounded-lg p-4">
          <Info className="w-4 h-4 text-blue-500 flex-shrink-0 mt-0.5" />
          <div className="text-xs text-blue-700 space-y-1">
            <p className="font-medium">What happens after upload?</p>
            <p>1. PDF is saved with a stable ID</p>
            <p>2. Text extraction (native PDF + OCR fallback)</p>
            <p>3. Claude AI extracts structured scientific data (server-side only)</p>
            <p>4. Summary (.md) and extraction (.json) files are generated</p>
            <p>5. Results are stored in the database for review and export</p>
          </div>
        </div>
      </div>
    </div>
  );
}
