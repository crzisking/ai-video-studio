import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// 开发期把后端 API 反代到 :8000，避免跨域；/ws 走 websocket 代理。
const backend = "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      "/object_info": backend,
      "/prompt": backend,
      "/history": backend,
      "/upload": backend,
      "/media": backend,
      "/uploads": backend,
      "/ws": { target: backend, ws: true },
    },
  },
});
