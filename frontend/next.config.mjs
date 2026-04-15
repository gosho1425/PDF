/** @type {import('next').NextConfig} */
const nextConfig = {
  eslint: {
    // Warnings don't block the build; errors in our pages are style-only.
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: false,
  },
};

export default nextConfig;
