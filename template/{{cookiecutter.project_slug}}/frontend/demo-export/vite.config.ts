import path from "node:path";
import { fileURLToPath } from "node:url";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import { viteSingleFile } from "vite-plugin-singlefile";

const dir = path.dirname(fileURLToPath(import.meta.url));

/**
 * Standalone single-file build of the demo replay.
 *
 * Reuses the REAL app components (DemoReplay -> MessageItem -> Recharts, etc.) and
 * the real `globals.css`, so the exported HTML looks 1:1 with the live demo page and
 * charts stay interactive. `vite-plugin-singlefile` inlines all JS + CSS into one
 * self-contained index.html. Next.js-only imports are aliased to tiny local shims.
 */
export default defineConfig({
  root: dir,
  plugins: [react(), viteSingleFile()],
  resolve: {
    alias: {
      "@": path.resolve(dir, "../src"),
      "next/image": path.resolve(dir, "shims/next-image.tsx"),
      "next/dynamic": path.resolve(dir, "shims/next-dynamic.ts"),
      "next/navigation": path.resolve(dir, "shims/next-navigation.ts"),
      "next/link": path.resolve(dir, "shims/next-link.tsx"),
      "next-intl": path.resolve(dir, "shims/next-intl.ts"),
    },
  },
  build: {
    outDir: path.resolve(dir, "dist"),
    emptyOutDir: true,
    assetsInlineLimit: 100_000_000,
    cssCodeSplit: false,
    chunkSizeWarningLimit: 8000,
  },
});
