/**
 * Vite configuration
 * Build tool configuration for the dashboard
 */
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'https://x5hp4ju4lj.execute-api.us-east-1.amazonaws.com',
        changeOrigin: true,
      },
    },
  },
});