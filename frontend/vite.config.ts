import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "../src/talent_radar/web",
    emptyOutDir: true,
  },
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: {
      "/auth": "http://127.0.0.1:8000",
      "/collection": "http://127.0.0.1:8000",
      "/comments": "http://127.0.0.1:8000",
      "/connections": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000",
      "/jobs": "http://127.0.0.1:8000",
      "/overview": "http://127.0.0.1:8000",
      "/posts": "http://127.0.0.1:8000",
      "/run-configurations": "http://127.0.0.1:8000",
      "/sources": "http://127.0.0.1:8000"
    }
  }
});
