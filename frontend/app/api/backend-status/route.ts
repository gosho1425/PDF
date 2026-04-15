/**
 * GET /api/backend-status
 *
 * Lightweight server-side health probe that checks whether the FastAPI
 * backend is reachable. The browser calls this endpoint on every page load
 * to determine if uvicorn is running.
 *
 * Returns:
 *   { ok: true,  version: "2.0.0" }   — backend is up
 *   { ok: false, reason: "…" }         — backend is down / unreachable
 */

import { NextResponse } from 'next/server';

const BACKEND = process.env.BACKEND_URL ?? 'http://localhost:8000';

export async function GET() {
  try {
    const res = await fetch(`${BACKEND}/health`, {
      signal: AbortSignal.timeout(3_000), // 3-second probe timeout
      cache: 'no-store',
    });

    if (res.ok) {
      const data = await res.json();
      return NextResponse.json({ ok: true, version: data.version ?? 'unknown' });
    }

    return NextResponse.json(
      { ok: false, reason: `Backend returned HTTP ${res.status}` },
      { status: 200 } // always 200 so the browser can read the body
    );
  } catch (err: unknown) {
    const msg =
      err instanceof Error ? err.message : String(err);

    const isDown =
      msg.includes('ECONNREFUSED') ||
      msg.includes('fetch failed') ||
      msg.includes('ENOTFOUND') ||
      msg.includes('timeout') ||
      msg.includes('ETIMEDOUT');

    return NextResponse.json(
      {
        ok: false,
        reason: isDown
          ? `Backend not running at ${BACKEND}. Start it with: cd backend && .venv\\Scripts\\activate && uvicorn app.main:app --reload`
          : msg,
      },
      { status: 200 }
    );
  }
}
