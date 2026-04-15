/**
 * Catch-all API proxy route.
 *
 * Every request to /api/proxy/* from the browser is handled HERE on the
 * Next.js server side, then forwarded to the FastAPI backend (localhost:8000).
 *
 * Why a Route Handler instead of next.config rewrites()?
 * - rewrites() can silently drop POST bodies in some Next.js 14 dev configs.
 * - Route Handlers run fully server-side: no CORS, no body-stripping, no CSRF.
 * - Works identically in local dev, sandbox, and production.
 *
 * Common error: "TypeError: fetch failed"
 *   → The FastAPI backend is NOT running. Start it with:
 *     cd backend && .venv\Scripts\activate && uvicorn app.main:app --reload
 */

import { NextRequest, NextResponse } from 'next/server';

const BACKEND = process.env.BACKEND_URL ?? 'http://localhost:8000';

async function proxy(req: NextRequest, { params }: { params: { path: string[] } }) {
  // Reconstruct the backend URL: /api/proxy/settings → /api/settings
  const pathSegments = params.path ?? [];
  const backendPath = `/api/${pathSegments.join('/')}`;
  const search = req.nextUrl.search ?? '';
  const targetUrl = `${BACKEND}${backendPath}${search}`;

  // Forward the request body for POST/PUT/PATCH
  let body: BodyInit | null = null;
  const method = req.method.toUpperCase();
  if (['POST', 'PUT', 'PATCH'].includes(method)) {
    body = await req.arrayBuffer();
  }

  // Build forwarded headers (keep Content-Type, drop hop-by-hop headers)
  const headers: Record<string, string> = {};
  req.headers.forEach((value, key) => {
    const lower = key.toLowerCase();
    if (['host', 'connection', 'transfer-encoding', 'keep-alive'].includes(lower)) return;
    headers[key] = value;
  });

  try {
    const backendRes = await fetch(targetUrl, {
      method,
      headers,
      body: body || undefined,
      // Don't follow redirects — pass them through
      redirect: 'manual',
      // Use a 10-minute timeout for slow LLM extraction calls
      signal: AbortSignal.timeout(600_000),
    });

    // Stream the response body back
    const resBody = await backendRes.arrayBuffer();
    const resHeaders = new Headers();
    backendRes.headers.forEach((value, key) => {
      // Strip hop-by-hop headers
      const lower = key.toLowerCase();
      if (['transfer-encoding', 'connection', 'keep-alive'].includes(lower)) return;
      resHeaders.set(key, value);
    });

    return new NextResponse(resBody, {
      status: backendRes.status,
      statusText: backendRes.statusText,
      headers: resHeaders,
    });
  } catch (err: unknown) {
    const isConnectionRefused =
      err instanceof Error &&
      (err.message.includes('ECONNREFUSED') ||
       err.message.includes('fetch failed') ||
       err.message.includes('ENOTFOUND') ||
       err.message.includes('connect ETIMEDOUT'));

    if (isConnectionRefused) {
      console.error(`[proxy] Backend not reachable at ${BACKEND} — is uvicorn running?`);
      return NextResponse.json(
        {
          error: 'Backend not running',
          detail:
            'FastAPI backend is not reachable at ' + BACKEND +
            '. Start it with: cd backend && .venv\\Scripts\\activate && uvicorn app.main:app --reload',
        },
        { status: 503 }
      );
    }

    console.error(`[proxy] Failed to reach backend at ${targetUrl}:`, err);
    return NextResponse.json(
      { error: 'Backend unreachable', detail: String(err) },
      { status: 502 }
    );
  }
}

export const GET     = proxy;
export const POST    = proxy;
export const PUT     = proxy;
export const PATCH   = proxy;
export const DELETE  = proxy;
export const OPTIONS = proxy;
