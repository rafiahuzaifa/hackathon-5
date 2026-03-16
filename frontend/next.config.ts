import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  output: 'standalone',
  reactStrictMode: true,
  images: {
    domains: ['localhost'],
  },
  // In production (Vercel), API calls go to the Python serverless function.
  // In local dev, they go to the FastAPI backend at port 8000.
  async rewrites() {
    const isProd = process.env.NODE_ENV === 'production';
    if (isProd) return [];          // Vercel handles routing via vercel.json
    return [
      {
        source: '/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/:path*`,
      },
    ];
  },
};

export default nextConfig;
