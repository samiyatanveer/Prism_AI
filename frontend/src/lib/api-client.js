/**
 * PrismAI API Client
 *
 * Axios instance with:
 *  - Base URL from environment
 *  - Request interceptor: attaches Bearer access token from Zustand store
 *  - Response interceptor: handles 401 → attempts silent token refresh once,
 *    then clears auth state and redirects to login on failure
 *
 * The access token lives in Zustand memory only.
 * The refresh token is an httpOnly cookie — never touched by JS.
 */

import axios from "axios";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true, // Required for httpOnly refresh token cookie
  headers: {
    "Content-Type": "application/json",
  },
});

// ── Request interceptor: attach access token ──────────────────────────────────
apiClient.interceptors.request.use(
  (config) => {
    // Dynamically import to avoid circular deps at module load time
    const { useAuthStore } = require("@/store/auth-store");
    const accessToken = useAuthStore.getState().accessToken;
    if (accessToken) {
      config.headers.Authorization = `Bearer ${accessToken}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ── Response interceptor: silent token refresh on 401 ────────────────────────
let _isRefreshing = false;
let _refreshSubscribers = [];

const subscribeTokenRefresh = (callback) => {
  _refreshSubscribers.push(callback);
};

const notifyRefreshSubscribers = (newToken) => {
  _refreshSubscribers.forEach((cb) => cb(newToken));
  _refreshSubscribers = [];
};

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    const is401 = error.response?.status === 401;
    const isAuthEndpoint =
      originalRequest.url?.includes("/auth/login") ||
      originalRequest.url?.includes("/auth/register") ||
      originalRequest.url?.includes("/auth/refresh");

    if (!is401 || isAuthEndpoint || originalRequest._retry) {
      return Promise.reject(error);
    }

    if (_isRefreshing) {
      return new Promise((resolve, reject) => {
        subscribeTokenRefresh((newToken) => {
          if (newToken) {
            originalRequest.headers.Authorization = `Bearer ${newToken}`;
            resolve(apiClient(originalRequest));
          } else {
            reject(error);
          }
        });
      });
    }

    originalRequest._retry = true;
    _isRefreshing = true;

    try {
      // POST to /auth/refresh — refresh token is sent automatically via httpOnly cookie
      const { data } = await apiClient.post("/auth/refresh");
      const newAccessToken = data.access_token;

      const { useAuthStore } = require("@/store/auth-store");
      useAuthStore.getState().setAccessToken(newAccessToken);

      originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
      notifyRefreshSubscribers(newAccessToken);

      return apiClient(originalRequest);
    } catch {
      notifyRefreshSubscribers(null);
      const { useAuthStore } = require("@/store/auth-store");
      useAuthStore.getState().clearAuth();

      if (typeof window !== "undefined") {
        // The interceptor runs outside a React component, where Next's router
        // is unavailable. Replace the protected history entry after expiry.
        window.location.replace("/login");
      }

      return Promise.reject(error);
    } finally {
      _isRefreshing = false;
    }
  }
);

export default apiClient;
