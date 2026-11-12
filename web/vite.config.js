import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

// 开发时 /api 代理到本地后端；生产构建后由 Express 托管 dist
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.VITE_API_TARGET || 'http://localhost:3210',
        changeOrigin: true
      }
    }
  }
});
