import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // Chế độ mock đọc data/banks_sample.json nằm ngoài thư mục frontend
  server: { fs: { allow: [fileURLToPath(new URL("..", import.meta.url))] } },
});
