import axios from 'axios';

// In Docker: VITE_API_URL=/api (proxied via nginx). In dev: direct localhost URL.
const baseURL = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:5000/api';

export const apiClient = axios.create({
  baseURL,
  headers: { 'Content-Type': 'application/json' },
});