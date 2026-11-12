import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const apiTarget = process.env.PDM_API_ORIGIN || "http://127.0.0.1:5051";
const parsedApi = new URL(apiTarget);
if (!["127.0.0.1", "localhost"].includes(parsedApi.hostname) || parsedApi.protocol !== "http:" || parsedApi.username || parsedApi.password || parsedApi.pathname !== "/") {
  throw new Error("Local preview API must be an explicit loopback HTTP origin");
}
const proxy = {
  "/api/v1": { target: parsedApi.origin, changeOrigin: false },
};
export default defineConfig({
  plugins: [react()],
  server: { host: "127.0.0.1", port: 5173, strictPort: true, proxy },
  preview: { host: "127.0.0.1", port: 5173, strictPort: true, proxy },
  build: { sourcemap: false },
});
