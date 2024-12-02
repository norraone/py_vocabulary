import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3000,
    host: true,
    proxy: {
      '^/api/.*': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
        secure: false,
        ws: true,
        rewrite: (path) => {
          console.log('[Vite Proxy] Rewriting path:', path)
          return path
        },
        configure: (proxy, options) => {
          proxy.on('error', (err, req, res) => {
            console.log('\n[Vite Proxy] Error:', {
              error: err.message,
              url: req.url,
              method: req.method,
              headers: req.headers
            })
          });
          
          proxy.on('proxyReq', (proxyReq, req, res) => {
            console.log('\n[Vite Proxy] Sending Request:', {
              method: req.method,
              url: req.url,
              headers: proxyReq.getHeaders(),
              target: options.target + req.url
            })
          });
          
          proxy.on('proxyRes', (proxyRes, req, res) => {
            console.log('\n[Vite Proxy] Received Response:', {
              status: proxyRes.statusCode,
              statusMessage: proxyRes.statusMessage,
              url: req.url,
              headers: proxyRes.headers
            })
          });
        }
      }
    }
  }
})
