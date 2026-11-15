import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Hôte du proxy CloudFront utilisé pour ouvrir l'app dans le navigateur.
const allowedHosts = ["d3l9rfbjymewy9.cloudfront.net"];

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, allowedHosts },
  preview: { allowedHosts },
});
