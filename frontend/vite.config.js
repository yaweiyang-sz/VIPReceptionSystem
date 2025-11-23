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
        target: process.env.NODE_ENV === 'development' ? 'http://localhost:8000' : 'http://backend:8000',
        changeOrigin: true,
        rewrite: (path) => path,
      },
      '/ws': {
        target: process.env.NODE_ENV === 'development' ? 'ws://localhost:8000' : 'ws://backend:8000',
        ws: true,
      }
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: true
  }
})
