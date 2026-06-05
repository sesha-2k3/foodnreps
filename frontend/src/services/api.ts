/**
 * Axios HTTP client with automatic silent token refresh.
 *
 * Design choice — shared refreshPromise prevents concurrent refresh storms:
 *   When multiple requests fire simultaneously with an expired access token,
 *   all receive 401. Without the shared promise, all would independently call
 *   POST /auth/refresh. The backend uses refresh token rotation — the first
 *   call succeeds and revokes the old token; all subsequent calls arrive with
 *   an already-revoked token and fail with 401. The user is logged out.
 *
 *   The shared promise ensures only one refresh call is in flight at a time.
 *   All 401 handlers await the same promise. The first handler starts it;
 *   the others wait for it. When it resolves, all retried requests get the
 *   same new access token.
 *
 * Design choice — no baseURL:
 *   The Vite proxy maps all backend route prefixes to localhost:8000. Axios
 *   uses relative paths (/auth/login, /client/workout). This means the
 *   frontend code contains no hardcoded host — production deployment is
 *   transparent (put a reverse proxy in front with the same path structure).
 *
 * Design choice — _retried flag prevents infinite 401 loops:
 *   If the refresh token itself is expired or revoked, POST /auth/refresh
 *   returns 401. Without the flag, the interceptor would try to refresh again,
 *   get 401 again, and loop forever. The flag marks a request as already
 *   retried — a second 401 on a retried request propagates as a real error.
 */

import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios';
import { tokenStore } from './auth';
import type { TokenResponse } from '../types';

// Augment Axios config with our custom _retried flag
declare module 'axios' {
  interface InternalAxiosRequestConfig {
    _retried?: boolean;
  }
}

export const api = axios.create({
  headers: { 'Content-Type': 'application/json' },
});

// ── Request interceptor: attach access token to every request ────────────────

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = tokenStore.get();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ── Shared refresh promise ────────────────────────────────────────────────────

let refreshPromise: Promise<string> | null = null;

// ── Response interceptor: silent token refresh on 401 ────────────────────────

api.interceptors.response.use(
  res => res,
  async (error: AxiosError) => {
    const config = error.config as InternalAxiosRequestConfig;

    // Only intercept 401s on non-retried requests
    if (
      error.response?.status !== 401 ||
      config._retried ||
      config.url === '/auth/refresh'   // ← never try to refresh a failed refresh
    ) {
      return Promise.reject(error);
    }

    // Start a shared refresh if one is not already in flight
    if (!refreshPromise) {
      refreshPromise = api
        .post<TokenResponse>('/auth/refresh')
        .then(res => {
          tokenStore.set(res.data.access_token);
          return res.data.access_token;
        })
        .finally(() => {
          refreshPromise = null;
        });
    }

    try {
      const newToken = await refreshPromise;
      config._retried = true;
      config.headers.Authorization = `Bearer ${newToken}`;
      return api(config);
    } catch {
      // Refresh itself failed — session is gone. Clear the token and
      // propagate the original error so callers can react (e.g. redirect to /login).
      tokenStore.clear();
      return Promise.reject(error);
    }
  }
);
