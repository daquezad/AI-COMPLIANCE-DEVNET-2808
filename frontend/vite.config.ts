/**
 * Copyright AGNTCY Contributors (https://github.com/agntcy)
 * SPDX-License-Identifier: Apache-2.0
 **/

import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"
import path from "path"

export default defineConfig({
  plugins: [react()],
  server: {
    fs: {
      strict: true,
      allow: [path.resolve(__dirname)],
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
    extensions: [".tsx", ".ts", ".jsx", ".js", ".json"],
  },
  build: {
    // Increase warning limit if you want to suppress warnings (optional)
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        // Manual chunks for better code splitting
        manualChunks: {
          // Vendor chunks - separate large libraries
          'vendor-react': ['react', 'react-dom'],
          'vendor-reactflow': ['@xyflow/react', '@reactflow/node-resizer'],
          'vendor-ui': ['lucide-react', 'react-icons', 'clsx', 'tailwind-merge', 'class-variance-authority'],
          'vendor-markdown': ['react-markdown', 'remark-gfm'],
          'vendor-utils': ['axios', 'uuid'],
        },
      },
    },
  },
})
