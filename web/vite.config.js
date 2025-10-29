import { defineConfig } from 'vite'

export default defineConfig({
  base: '/static/',
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000'
    }
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true
  }
})
