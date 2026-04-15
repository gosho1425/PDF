/** @type {import('next').NextConfig} */
const nextConfig = {
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: false,
  },
  // ── API proxy ──────────────────────────────────────────────────────────────
  // All /api/* and /health requests from the browser are forwarded to the
  // FastAPI backend on port 8000.  This means the browser NEVER calls port
  // 8000 directly — no CORS issues, works in both local and sandbox envs.
  async rewrites() {
    const backendUrl = process.env.BACKEND_URL ?? 'http://localhost:8000';
    return [
      { source: '/api/:path*',  destination: `${backendUrl}/api/:path*` },
      { source: '/health',      destination: `${backendUrl}/health` },
    ];
  },
};

export default nextConfig;
