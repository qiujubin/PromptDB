import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    host: '127.0.0.1',
    port: 4163,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:4165',
        changeOrigin: true,
      },
    },
  },
})