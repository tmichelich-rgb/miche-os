import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Redirect root to the SPA for now (during migration)
  async redirects() {
    return [
      {
        source: '/app',
        destination: '/legacy/app.html',
        permanent: false,
      },
      {
        source: '/admin',
        destination: '/legacy/admin.html',
        permanent: false,
      },
    ];
  },
  // Allow Shopify domains for images
  images: {
    remotePatterns: [
      { protocol: 'https', hostname: '**.shopify.com' },
      { protocol: 'https', hostname: '**.googleusercontent.com' },
    ],
  },
  // Vercel cron jobs configured in vercel.json
};

export default nextConfig;
