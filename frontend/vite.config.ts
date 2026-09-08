import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// The app calls the backend at its absolute URL (VITE_API_URL), so there is no
// dev proxy here — CORS on the backend is what allows the cross-origin call.
export default defineConfig({
  plugins: [react()],
});
