/**
 * TanStack Query client configuration.
 *
 * Sensible defaults:
 *  - staleTime: 30s — avoid refetching on every mount for stable data
 *  - retry: only on non-4xx errors (4xx = client error, retrying won't help)
 *  - refetchOnWindowFocus: disabled in development to reduce noise
 */

import { QueryClient } from "@tanstack/react-query";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30 * 1000, // 30 seconds
      gcTime: 5 * 60 * 1000, // 5 minutes
      retry: (failureCount, error) => {
        // Don't retry on 4xx client errors
        if (error?.response?.status >= 400 && error?.response?.status < 500) {
          return false;
        }
        return failureCount < 2;
      },
      refetchOnWindowFocus: process.env.NODE_ENV === "production",
    },
    mutations: {
      retry: false,
    },
  },
});

export default queryClient;
