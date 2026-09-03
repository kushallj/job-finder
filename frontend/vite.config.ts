import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  base: './',
  plugins: [react()],

  server: {
    host: '0.0.0.0', // Listen on all network interfaces for mobile & ngrok access
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/run-query': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
