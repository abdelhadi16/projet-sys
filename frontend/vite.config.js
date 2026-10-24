// Vite configuration for the React frontend.
// - The dev server runs on port 5173 (the origin the FastAPI backend already
//   allows via CORS in main.py).
// - The `test` block wires up Vitest with jsdom so we can render React
//   components in a fake browser during unit tests.
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.js",
  },
});
