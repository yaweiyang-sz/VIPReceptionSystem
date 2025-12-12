import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/api': {
        // In Docker, backend service is available at backend:8000
        // For local development without Docker, use localhost:8000
        target: process.env.VITE_API_TARGET || 'http://backend:8000',
        changeOrigin: true,
        rewrite: (path) => path,
        ws: true,  // Enable WebSocket proxy for all API endpoints including camera streams
      }
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: true
  }
})
