"use client";

/**
 * Global providers wrapper.
 *
 * Wrap children with all client-side providers here. Order matters:
 *  1. QueryClientProvider — all hooks need this
 *  2. AuthHydrationProvider — silently re-establishes session on mount
 *
 * Add new providers here as features are added (theme, toast, etc.)
 */

import { QueryClientProvider } from "@tanstack/react-query";
import queryClient from "@/lib/query-client";
import AuthHydrationProvider from "./auth-hydration-provider";

export default function Providers({ children }) {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthHydrationProvider>{children}</AuthHydrationProvider>
    </QueryClientProvider>
  );
}
