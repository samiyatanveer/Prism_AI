"use client";

/**
 * Auth Hydration Provider
 *
 * On every app mount, attempts a silent token refresh by calling /auth/refresh.
 * The httpOnly refresh token cookie is sent automatically by the browser.
 * If it succeeds, the auth store is hydrated with the new access token + user.
 * If it fails (no cookie, expired), the user is treated as unauthenticated.
 *
 * This restores sessions across page refreshes without localStorage.
 */

import { useEffect } from "react";
import { useAuthStore } from "@/store/auth-store";
import apiClient from "@/lib/api-client";

export default function AuthHydrationProvider({ children }) {
  const { setAuth, setHydrated } = useAuthStore();

  useEffect(() => {
    let cancelled = false;

    async function hydrate() {
      try {
        // Attempt silent refresh — sends the httpOnly cookie automatically
        const refreshRes = await apiClient.post("/auth/refresh");
        const { access_token } = refreshRes.data;

        // Fetch the user profile with the new token
        const meRes = await apiClient.get("/auth/me", {
          headers: { Authorization: `Bearer ${access_token}` },
        });

        if (!cancelled) {
          setAuth(meRes.data, access_token);
        }
      } catch {
        // No valid session — that's fine, unauthenticated state is normal
        if (!cancelled) {
          setHydrated();
        }
      }
    }

    hydrate();

    return () => {
      cancelled = true;
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return children;
}
