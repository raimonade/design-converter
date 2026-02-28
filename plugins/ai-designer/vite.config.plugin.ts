import { defineConfig } from "vite";
import { resolve } from "path";

export default defineConfig({
  build: {
    outDir: "dist",
    emptyOutDir: false,
    lib: {
      entry: resolve(__dirname, "src/plugin/code.ts"),
      name: "code",
      formats: ["iife"],
      fileName: () => "code.js",
    },
    rollupOptions: {
      output: {
        extend: true,
      },
    },
    minify: false,
    target: "es2017", // Figma supports ES2017
  },
  esbuild: {
    target: "es2017",
    // Replace ?? with || for compatibility
    define: {},
  },
});
