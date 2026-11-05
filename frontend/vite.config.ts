import { fileURLToPath, URL } from 'node:url'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

// Build servido pelo Flask em /static (mesma origem da API: sem CORS).
// Em desenvolvimento (npm run dev), /api e /health vão para o stack Docker em :8080.
export default defineConfig({
  base: '/static/',
  plugins: [react(), tailwindcss()],
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  server: {
    proxy: {
      '/api': 'http://localhost:8080',
      '/health': 'http://localhost:8080',
    },
  },
  build: { outDir: 'dist', emptyOutDir: true, chunkSizeWarningLimit: 800 },
})
