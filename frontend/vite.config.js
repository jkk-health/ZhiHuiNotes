import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 开发态：/api 代理到 Flask（5000），免跨域；构建态：产物由 Flask 托管
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
    },
  },
})
