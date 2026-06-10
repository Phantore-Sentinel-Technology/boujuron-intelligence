import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/fraud-alerts": "http://localhost:8002",
      "/events": "http://localhost:8002",
      "/ml-features": "http://localhost:8002",
      "/users": "http://localhost:8002",
      "/auth": "http://localhost:8002",
      "/customers": "http://localhost:8002",
      "/cases": "http://localhost:8002",
      "/analytics": "http://localhost:8002",
      "/intelligence": "http://localhost:8002",
      "/export": "http://localhost:8002",
      "/reports": "http://localhost:8002"
    }
  }
});
