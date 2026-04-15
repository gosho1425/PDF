/** @type {import('next').NextConfig} */
const nextConfig = {
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: false,
  },
  // NOTE: /api/* is now handled by app/api/proxy/[...path]/route.ts (server-side proxy).
  // We only keep a rewrite for /health so the health check endpoint is also reachable.
  async rewrites() {
    const backendUrl = process.env.BACKEND_URL ?? 'http://localhost:8000';
    return [
      { source: '/health', destination: `${backendUrl}/health` },
    ];
  },
};

export default nextConfig;
