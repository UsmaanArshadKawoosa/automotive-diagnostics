import axios, { type AxiosInstance, type AxiosError, type InternalAxiosRequestConfig } from 'axios';
import type { ApiError } from '../types/api';

const RAW_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const API_BASE = RAW_BASE.replace(/\/+$/, '');

function getToken(): string | null {
  return localStorage.getItem('auth_token');
}

function setToken(token: string | null): void {
  if (token) {
    localStorage.setItem('auth_token', token);
  } else {
    localStorage.removeItem('auth_token');
  }
}

export const apiClient: AxiosInstance = axios.create({
  baseURL: `${API_BASE}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = getToken();
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiError>) => {
    const message =
      (error.response?.data &&
        typeof error.response.data === 'object' &&
        'detail' in error.response.data &&
        typeof error.response.data.detail === 'string'
        ? error.response.data.detail
        : error.message) ||
      'An unexpected error occurred';
    return Promise.reject(new Error(message));
  }
);

export { API_BASE, getToken, setToken };
