/**
 * API client for communicating with the FastAPI backend.
 *
 * SECURITY NOTE: This file only communicates with OUR backend.
 * The backend is responsible for all LLM API calls.
 * No API keys are ever included here.
 */

import axios from 'axios';
import type {
  PaperListResponse,
  PaperDetail,
  ExtractionRecord,
  UploadResult,
  ExportRequest,
} from '@/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const API_V1 = `${API_BASE}/api/v1`;

export const apiClient = axios.create({
  baseURL: API_V1,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const message =
      error.response?.data?.detail ||
      error.response?.data?.message ||
      error.message ||
      'An unexpected error occurred';
    return Promise.reject(new Error(message));
  }
);

// ── Papers API ─────────────────────────────────────────────────────────────────

export const papersApi = {
  list: async (params: {
    skip?: number;
    limit?: number;
    status?: string;
    search?: string;
    sort_by?: string;
    sort_order?: string;
  }): Promise<PaperListResponse> => {
    const response = await apiClient.get('/papers', { params });
    return response.data;
  },

  get: async (paperId: string): Promise<PaperDetail> => {
    const response = await apiClient.get(`/papers/${paperId}`);
    return response.data;
  },

  upload: async (files: File[]): Promise<UploadResult[]> => {
    const formData = new FormData();
    files.forEach((file) => formData.append('files', file));
    const response = await apiClient.post('/papers/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 60000,
    });
    return response.data;
  },

  scanFolder: async (folderPath: string): Promise<{ task_id: string; status: string }> => {
    const response = await apiClient.post('/papers/scan-folder', null, {
      params: { folder_path: folderPath },
    });
    return response.data;
  },

  update: async (
    paperId: string,
    data: Partial<Pick<PaperDetail, 'title' | 'doi' | 'abstract' | 'publication_year' | 'keywords'>>
  ): Promise<void> => {
    await apiClient.patch(`/papers/${paperId}`, data);
  },

  reprocess: async (paperId: string, stage: 'full' | 'parse' | 'extract' = 'full') => {
    const response = await apiClient.post(`/papers/${paperId}/reprocess`, null, {
      params: { stage },
    });
    return response.data;
  },

  downloadSummary: (paperId: string): string =>
    `${API_V1}/papers/${paperId}/summary`,

  downloadExtractionJson: (paperId: string): string =>
    `${API_V1}/papers/${paperId}/extraction-json`,

  delete: async (paperId: string): Promise<void> => {
    await apiClient.delete(`/papers/${paperId}`);
  },
};

// ── Extractions API ────────────────────────────────────────────────────────────

export const extractionsApi = {
  get: async (paperId: string): Promise<ExtractionRecord> => {
    const response = await apiClient.get(`/extractions/${paperId}`);
    return response.data;
  },

  update: async (paperId: string, data: Partial<ExtractionRecord>): Promise<void> => {
    await apiClient.patch(`/extractions/${paperId}`, data);
  },

  getEvidence: async (paperId: string, fieldName?: string) => {
    const response = await apiClient.get(`/extractions/${paperId}/evidence`, {
      params: fieldName ? { field_name: fieldName } : undefined,
    });
    return response.data;
  },
};

// ── Jobs API ───────────────────────────────────────────────────────────────────

export const jobsApi = {
  list: async (paperId?: string) => {
    const response = await apiClient.get('/jobs', {
      params: paperId ? { paper_id: paperId } : undefined,
    });
    return response.data;
  },

  getCeleryStatus: async (taskId: string) => {
    const response = await apiClient.get(`/jobs/${taskId}/celery-status`);
    return response.data;
  },
};

// ── Export API ─────────────────────────────────────────────────────────────────

export const exportApi = {
  exportPapers: async (request: ExportRequest): Promise<Blob> => {
    const response = await apiClient.post('/export/papers', request, {
      responseType: 'blob',
      timeout: 60000,
    });
    return response.data;
  },

  downloadFile: (blob: Blob, filename: string): void => {
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  },
};
