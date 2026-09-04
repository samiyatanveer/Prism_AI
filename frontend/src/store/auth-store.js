/**
 * Zustand auth store.
 *
 * Security model:
 *  - accessToken: kept in Zustand memory ONLY — never written to localStorage,
 *    sessionStorage, cookies, or any browser storage. Lost on page refresh
 *    (intentional — the silent refresh via httpOnly cookie restores it).
 *  - refreshToken: managed entirely as an httpOnly cookie by the server.
 *    JS has zero read/write access to it.
 *  - user: safe public fields only (id, email, role) — no credentials.
 */

import { create } from "zustand";

const useAuthStore = create((set) => ({
  // ── State ──────────────────────────────────────────────────────────────────
  user: null,
  accessToken: null,
  isAuthenticated: false,
  isHydrating: true, // true while we're attempting a silent refresh on mount

  // ── Actions ────────────────────────────────────────────────────────────────

  /**
   * Set auth state after a successful login/register/refresh.
   * @param {object} user - Safe user object (no passwords or credentials)
   * @param {string} accessToken - Short-lived JWT access token
   */
  setAuth: (user, accessToken) =>
    set({
      user,
      accessToken,
      isAuthenticated: true,
      isHydrating: false,
    }),

  /**
   * Update just the access token (e.g. after a silent refresh).
   */
  setAccessToken: (accessToken) => set({ accessToken }),

  /**
   * Clear all auth state — called on logout or auth failure.
   * The httpOnly cookie is cleared server-side by the /auth/logout endpoint.
   */
  clearAuth: () =>
    set({
      user: null,
      accessToken: null,
      isAuthenticated: false,
      isHydrating: false,
    }),

  /**
   * Mark hydration as complete without setting auth (no valid session).
   */
  setHydrated: () => set({ isHydrating: false }),
}));

export { useAuthStore };
