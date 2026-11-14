import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// strictPort: backend CORS sirf http://localhost:5173 allow karta hai,
// isliye port badalna nahi chahiye.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    strictPort: true,
  },
  test: {
    environment: 'jsdom',
    // jsdom ka origin fix: API base isi origin ke andar rakha hai, taaki CORS na lage
    environmentOptions: { jsdom: { url: 'http://localhost:3000' } },
    globals: true,
    setupFiles: './src/test/setup.js',
    include: ['src/test/**/*.test.{js,jsx}'],
    css: false,
    env: { VITE_API_BASE_URL: 'http://localhost:3000/api' },
  },
})