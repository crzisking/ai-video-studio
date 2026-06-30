import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// 前端跑在 :3000，把后端各 API 前缀代理到 FastAPI :8000（免 CORS，前端用相对路径）
const backend = "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      "/projects": backend,
      "/providers": backend,
      "/jobs": backend,
      "/media": backend,
      "/uploads": backend,
      "/health": backend,
    },
  },
});
