import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'

/**
 * Vite configuration with dev server proxy.
 *
 * Design choice — proxy rather than direct cross-origin calls:
 *   The backend runs at localhost:8000 and the Vite dev server at localhost:5173.
 *   Proxying all /auth, /client, /trainer, etc. routes to localhost:8000 makes
 *   the browser see every API call as same-origin (localhost:5173). This means:
 *   - The httpOnly refresh token cookie is set and sent as same-origin, avoiding
 *     any browser-specific cross-origin cookie handling quirks.
 *   - Axios needs no base URL — all paths are relative (/auth/login, not http://...).
 *   - Production deployment is transparent: swap the proxy target or put a reverse
 *     proxy (nginx) in front with the same path structure.
 */
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/auth':         { target: 'http://localhost:8000', changeOrigin: true },
      '/client':       { target: 'http://localhost:8000', changeOrigin: true },
      '/trainer':      { target: 'http://localhost:8000', changeOrigin: true },
      '/nutritionist': { target: 'http://localhost:8000', changeOrigin: true },
      '/coach':        { target: 'http://localhost:8000', changeOrigin: true },
      '/admin':        { target: 'http://localhost:8000', changeOrigin: true },
      '/personal':     { target: 'http://localhost:8000', changeOrigin: true },
      '/health':       { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
})