/**
 * Catch-all API proxy route.
 *
 * Every request to /api/* from the browser is handled HERE on the server side,
 * then forwarded to the FastAPI backend (localhost:8000).
 *
 * Why a Route Handler instead of next.config rewrites()?
 * - rewrites() can silently drop POST bodies in some Next.js 14 dev configs.
 * - Route Handlers run fully server-side: no CORS, no body-stripping, no CSRF.
 * - Works identically in local dev, sandbox, and production.
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

  // Build forwarded headers (keep Content-Type, drop Host)
  const headers: Record<string, string> = {};
  req.headers.forEach((value, key) => {
    // Skip headers that should not be forwarded
    if (['host', 'connection', 'transfer-encoding'].includes(key.toLowerCase())) return;
    headers[key] = value;
  });

  try {
    const backendRes = await fetch(targetUrl, {
      method,
      headers,
      body: body || undefined,
      // Don't follow redirects — pass them through
      redirect: 'manual',
    });

    // Stream the response body back
    const resBody = await backendRes.arrayBuffer();
    const resHeaders = new Headers();
    backendRes.headers.forEach((value, key) => {
      // Strip hop-by-hop headers
      if (['transfer-encoding', 'connection', 'keep-alive'].includes(key.toLowerCase())) return;
      resHeaders.set(key, value);
    });

    return new NextResponse(resBody, {
      status: backendRes.status,
      statusText: backendRes.statusText,
      headers: resHeaders,
    });
  } catch (err) {
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
