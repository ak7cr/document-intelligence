// src/api/client.ts
import axios from 'axios';

export const apiClient = axios.create({
  baseURL: 'http://127.0.0.1:5000/api', // Points to your Flask backend
  headers: {
    'Content-Type': 'application/json',
  },
});