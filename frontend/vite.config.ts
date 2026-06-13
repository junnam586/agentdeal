import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Proxy API calls to the FastAPI backend on :8000 during dev so the frontend can
// use relative paths. SSE works through the proxy.
export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    // Use 127.0.0.1 (not "localhost") so the proxy target can't resolve to IPv6
    // ::1 while the backend listens on IPv4.
    proxy: {
      "/negotiate": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/negotiations": { target: "http://127.0.0.1:8000", changeOrigin: true },
    },
  },
});
