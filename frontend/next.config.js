/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  env: {
    // NEXT_PUBLIC_ prefix makes it available in browser.
    // IMPORTANT: Never put API keys in NEXT_PUBLIC_ variables.
    // The backend URL is safe to expose (it's just an address, not a secret).
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  },
  async rewrites() {
    // In development, proxy /api calls to the FastAPI backend
    if (process.env.NODE_ENV === 'development') {
      return [
        {
          source: '/api/:path*',
          destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/:path*`,
        },
      ]
    }
    return []
  },
}

module.exports = nextConfig
