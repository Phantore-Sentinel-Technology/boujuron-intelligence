import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/fraud-alerts": "http://localhost:8002",
      "/events": "http://localhost:8002",
      "/ml-features": "http://localhost:8002",
      "/users": "http://localhost:8002"
    }
  }
});
