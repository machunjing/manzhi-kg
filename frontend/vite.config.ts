import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    port: 5178,
    host: '127.0.0.1',
    open: false,
    proxy: {
      // 开发时把 /api 转发到本地 Flask，避免跨域与硬编码地址
      '/api': {
        target: 'http://127.0.0.1:5001',
        changeOrigin: true
      }
    }
  }
})
