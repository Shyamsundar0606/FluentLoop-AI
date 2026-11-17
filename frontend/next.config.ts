import type { NextConfig } from "next";

const nextConfig: NextConfig = {
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
