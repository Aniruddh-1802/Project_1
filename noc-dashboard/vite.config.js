import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/network': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/pipeline': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
