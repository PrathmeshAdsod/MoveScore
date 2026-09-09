import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  // Backend URL is injected at build time for the standalone container
  env: {
    NEXT_PUBLIC_BACKEND_URL: process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8080",
  },
};

export default nextConfig;
