import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
export default defineConfig(({ mode }) => {
  const target =
    loadEnv(mode, ".", "").VITE_API_TARGET || "http://localhost:8080";
  return {
    plugins: [react(), tailwindcss()],
    server: {
      proxy: {
        "/api": { target },
        "/actuator": { target },
      },
    },
  };
});
