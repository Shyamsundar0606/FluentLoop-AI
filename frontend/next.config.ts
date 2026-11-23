import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Browser tests must not share the live personal server's development cache.
  distDir: process.env.FLUENTLOOP_E2E_BUILD === "1" ? ".next-e2e" : ".next",
  output: process.env.FLUENTLOOP_STANDALONE === "1" ? "standalone" : undefined,
  /* config options here */
  cacheComponents: true,
  partialPrefetching: true,
  devIndicators: false,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
