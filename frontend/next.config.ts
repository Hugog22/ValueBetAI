import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  generateBuildId: async () => 'cache-bust-v3',
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "images.unsplash.com",
      },
      {
        protocol: "https",
        hostname: "upload.wikimedia.org",
      },
    ],
  },
};

export default nextConfig;
