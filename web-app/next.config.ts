import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    // Use environment variable for API base URL, fallback to localhost for development
    const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'https://nodecel.com';
    
    return [
      {
        source: "/roleplay/:path*",
        destination: `${apiBaseUrl}/roleplay/:path*`,
      },
    ];
  },
};

export default nextConfig;
