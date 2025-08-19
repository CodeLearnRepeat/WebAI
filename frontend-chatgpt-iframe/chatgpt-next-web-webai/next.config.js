/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    appDir: false, // Use pages directory for compatibility
  },
  
  // Enable standalone output for better deployment
  output: 'standalone',
  
  // Disable x-powered-by header
  poweredByHeader: false,
  
  // Enable compression
  compress: true,
  
  // Configure headers for iframe embedding
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'X-Frame-Options',
            value: 'ALLOWALL', // Allow embedding in iframes
          },
          {
            key: 'Content-Security-Policy',
            value: `
              frame-ancestors 'self' https://storage.googleapis.com https://*.googleapis.com *;
              default-src 'self';
              script-src 'self' 'unsafe-eval' 'unsafe-inline' https://cdn.jsdelivr.net;
              style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com;
              font-src 'self' https://fonts.gstatic.com;
              img-src 'self' data: https:;
              connect-src 'self' https: wss:;
            `.replace(/\s+/g, ' ').trim()
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin',
          },
        ],
      },
      {
        // Special headers for embedded pages
        source: '/embedded/:path*',
        headers: [
          {
            key: 'X-Frame-Options',
            value: 'ALLOWALL',
          },
          {
            key: 'Cross-Origin-Embedder-Policy',
            value: 'unsafe-none',
          },
        ],
      },
    ];
  },

  // Environment variables that should be exposed to the browser
  env: {
    NEXT_PUBLIC_WEBAI_API_URL: process.env.NEXT_PUBLIC_WEBAI_API_URL,
    NEXT_PUBLIC_WEBAI_DEBUG: process.env.NEXT_PUBLIC_WEBAI_DEBUG,
  },

  // Webpack configuration for better bundling
  webpack: (config, { isServer }) => {
    // Optimize for iframe usage
    if (!isServer) {
      config.resolve.fallback = {
        ...config.resolve.fallback,
        fs: false,
        net: false,
        tls: false,
      };
    }

    // Add support for importing markdown files
    config.module.rules.push({
      test: /\.md$/,
      use: 'raw-loader',
    });

    return config;
  },

  // Image optimization settings
  images: {
    domains: ['storage.googleapis.com', 'cdn.jsdelivr.net'],
    unoptimized: true, // Disable for iframe compatibility
  },

  // Trailing slash configuration
  trailingSlash: false,

  // Disable telemetry
  telemetry: false,

  // React strict mode
  reactStrictMode: true,

  // SWC minification
  swcMinify: true,

  // Configure redirects for embedded mode
  async redirects() {
    return [
      {
        source: '/chat',
        has: [
          {
            type: 'query',
            key: 'embedded',
            value: 'true',
          },
        ],
        destination: '/embedded/chat',
        permanent: false,
      },
    ];
  },

  // Configure rewrites for API proxying if needed
  async rewrites() {
    return [
      {
        source: '/api/webai/:path*',
        destination: `${process.env.NEXT_PUBLIC_WEBAI_API_URL || 'http://localhost:8000'}/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;