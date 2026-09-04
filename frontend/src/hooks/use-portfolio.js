/**
 * TanStack Query hooks for portfolio data.
 */

import { useQuery } from "@tanstack/react-query";
import apiClient from "@/lib/api-client";

export const portfolioKeys = {
  all: ["portfolio"],
  holdings: () => [...portfolioKeys.all, "holdings"],
};

/**
 * Fetch live portfolio holdings from the user's active exchange.
 * USD values are nullable — handle null in the UI without fabricating values.
 */
export function usePortfolio() {
  return useQuery({
    queryKey: portfolioKeys.holdings(),
    queryFn: async () => {
      // A stalled upstream exchange request must reject so React Query leaves
      // its loading state and the page can render its existing error UI.
      const { data } = await apiClient.get("/portfolio", { timeout: 30000 });
      return data;
    },
    staleTime: 60 * 1000, // 60s — portfolio is live data, refresh more frequently
    retry: (count, error) => {
      // Don't retry 424 (no exchange connected) or 429 (rate limit)
      if (error?.response?.status === 424) return false;
      if (error?.response?.status === 429) return false;
      return count < 1;
    },
  });
}
