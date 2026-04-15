/**
 * API client.
 *
 * All requests go through the Next.js Route Handler at /api/proxy/*
 * which proxies them server-side to FastAPI on port 8000.
 *
 * This means:
 *  - The browser never touches port 8000 directly → no CORS issues.
 *  - POST bodies are forwarded reliably (no next.config rewrite body-stripping).
 *  - Works identically on localhost, sandbox, and any remote server.
 *  - The ANTHROPIC_API_KEY is NEVER exposed here — it lives in backend/.env only.
 */

import axios from 'axios';

// Base URL for the proxy: same origin, /api/proxy prefix.
// NEXT_PUBLIC_API_URL can override (e.g. if running frontend standalone).
const BASE = process.env.NEXT_PUBLIC_API_URL
  ? `${process.env.NEXT_PUBLIC_API_URL}/api`
  : '/api/proxy';

export const api = axios.create({
  baseURL: BASE,
  timeout: 300_000, // 5 min — LLM extraction calls can be slow
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.response.use(
  (r) => r,
  (err) => {
    // 503 means the Next.js proxy could not reach the FastAPI backend
    if (err.response?.status === 503) {
      const detail = err.response?.data?.detail ?? '';
      return Promise.reject(
        new Error(
          'Backend not running. Start it with: cd backend && .venv\\Scripts\\activate && uvicorn app.main:app --reload' +
          (detail ? `\n(${detail})` : '')
        )
      );
    }
    const msg =
      err.response?.data?.detail ||
      err.response?.data?.error ||
      err.message ||
      'Unknown error';
    return Promise.reject(new Error(String(msg)));
  }
);

// ── Settings ──────────────────────────────────────────────────────────────────
export const settingsApi = {
  get:            ()                      => api.get('/settings').then(r => r.data),
  update:         (data: { paper_folder?: string; custom_parameters?: object[] }) =>
                    api.post('/settings', data).then(r => r.data),
  validateFolder: (folder: string)        =>
                    api.post('/settings/validate-folder', { folder }).then(r => r.data),
  getLlm:         ()                      => api.get('/settings/llm').then(r => r.data),
};

// ── Scan ──────────────────────────────────────────────────────────────────────
export const scanApi = {
  run:    (custom_parameters?: object[]) =>
            api.post('/scan', { custom_parameters }).then(r => r.data),
  status: ()                             => api.get('/scan/status').then(r => r.data),
};

// ── Papers ────────────────────────────────────────────────────────────────────
export const papersApi = {
  list: (params?: {
    skip?: number; limit?: number; status?: string;
    search?: string; sort_by?: string; sort_order?: string;
  }) => api.get('/papers', { params }).then(r => r.data),

  get: (id: string) =>
    api.get(`/papers/${id}`).then(r => r.data),

  summary: (id: string) =>
    api.get(`/papers/${id}/summary`, { responseType: 'text' }).then(r => r.data as string),

  reprocess: (id: string) =>
    api.post(`/papers/${id}/reprocess`).then(r => r.data),

  delete: (id: string) =>
    api.delete(`/papers/${id}`),
};
