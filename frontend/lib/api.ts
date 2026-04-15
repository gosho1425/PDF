/**
 * API client — communicates with the local FastAPI backend on port 8000.
 * The API key is NEVER exposed here — it lives in backend/.env only.
 */

import axios from 'axios';

const BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export const api = axios.create({
  baseURL: BASE,
  timeout: 300_000, // 5 min — LLM calls can be slow
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.response.use(
  (r) => r,
  (err) => {
    const msg =
      err.response?.data?.detail ||
      err.response?.data?.error ||
      err.message ||
      'Unknown error';
    return Promise.reject(new Error(msg));
  }
);

// ── Settings ──────────────────────────────────────────────────────────────────
export const settingsApi = {
  get: () => api.get('/api/settings').then(r => r.data),
  update: (data: { paper_folder?: string; custom_parameters?: object[] }) =>
    api.post('/api/settings', data).then(r => r.data),
  validateFolder: (folder: string) =>
    api.post('/api/settings/validate-folder', { folder }).then(r => r.data),
  getLlm: () => api.get('/api/settings/llm').then(r => r.data),
};

// ── Scan ──────────────────────────────────────────────────────────────────────
export const scanApi = {
  run: (custom_parameters?: object[]) =>
    api.post('/api/scan', { custom_parameters }).then(r => r.data),
  status: () => api.get('/api/scan/status').then(r => r.data),
};

// ── Papers ────────────────────────────────────────────────────────────────────
export const papersApi = {
  list: (params?: {
    skip?: number; limit?: number; status?: string;
    search?: string; sort_by?: string; sort_order?: string;
  }) => api.get('/api/papers', { params }).then(r => r.data),

  get: (id: string) => api.get(`/api/papers/${id}`).then(r => r.data),

  summary: (id: string) =>
    api.get(`/api/papers/${id}/summary`, { responseType: 'text' }).then(r => r.data as string),

  reprocess: (id: string) =>
    api.post(`/api/papers/${id}/reprocess`).then(r => r.data),

  delete: (id: string) => api.delete(`/api/papers/${id}`),
};
