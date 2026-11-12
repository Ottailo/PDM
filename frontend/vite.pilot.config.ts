import { fileURLToPath } from "node:url";
import { readFileSync } from "node:fs";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const root = fileURLToPath(new URL("./pilot", import.meta.url));
const publicDir = fileURLToPath(new URL("./public", import.meta.url));
const outDir = fileURLToPath(new URL("./dist-pilot", import.meta.url));

export default defineConfig({
  root,
  publicDir,
  plugins: [
    react(),
    {
      name: "public-pilot-unavailable-api",
      configurePreviewServer(server) {
        server.middlewares.use((request, response, next) => {
          const pathname = new URL(request.url || "/", "http://localhost").pathname;
          if (pathname === "/api" || pathname.startsWith("/api/")) {
            response.writeHead(503, {
              "Content-Type": "application/json; charset=utf-8",
              "Cache-Control": "no-store",
              "X-Content-Type-Options": "nosniff",
            });
            response.end(readFileSync(new URL("./public/pilot-unavailable.json", import.meta.url)));
            return;
          }
          next();
        });
      },
    },
  ],
  preview: { host: "127.0.0.1", port: 5175, strictPort: true },
  build: { outDir, emptyOutDir: true, sourcemap: false },
});
