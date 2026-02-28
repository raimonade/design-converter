import { defineConfig } from "vite";
import preact from "@preact/preset-vite";
import tailwindcss from "@tailwindcss/vite";
import { viteSingleFile } from "vite-plugin-singlefile";
import { resolve } from "path";

export default defineConfig({
  plugins: [preact(), tailwindcss(), viteSingleFile()],
  root: "src/ui",
  publicDir: false,
  build: {
    outDir: resolve(__dirname, "dist"),
    emptyOutDir: false,
    rollupOptions: {
      input: resolve(__dirname, "src/ui/index.html"),
      output: {
        entryFileNames: "ui.js",
        assetFileNames: "ui.[ext]",
      },
    },
    target: "es2017",
  },
});
