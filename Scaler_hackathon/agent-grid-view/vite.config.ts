import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";

// https://vitejs.dev/config/
export default defineConfig(() => ({
  server: {
    host: "::",
    port: 8080,
    proxy: Object.fromEntries(
      [
        "/health",
        "/ready",
        "/state",
        "/policies",
        "/workloads",
        "/nodes",
        "/reset",
        "/step",
        "/run",
        "/benchmarks",
        "/history",
        "/exports",
      ].map((path) => [path, "http://127.0.0.1:7861"]),
    ),
    hmr: {
      overlay: false,
    },
  },
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
    dedupe: ["react", "react-dom", "react/jsx-runtime", "react/jsx-dev-runtime", "@tanstack/react-query", "@tanstack/query-core"],
  },
}));
