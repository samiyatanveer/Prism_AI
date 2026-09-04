/**
 * TanStack Query hooks for market data.
 */

import { useQuery } from "@tanstack/react-query";
import apiClient from "@/lib/api-client";

export const marketKeys = {
  ticker: (symbol) => ["market", symbol, "ticker"],
  candles: (symbol, interval, limit) => ["market", symbol, "candles", interval, limit],
};

/** Fetch 24-hour ticker statistics for a symbol. */
export function useTicker(symbol) {
  return useQuery({
    queryKey: marketKeys.ticker(symbol),
    queryFn: async () => {
      const { data } = await apiClient.get(`/market/${symbol}/ticker`);
      return data;
    },
    enabled: !!symbol,
    staleTime: 30 * 1000, // 30s
    retry: (count, error) => {
      if (error?.response?.status === 424) return false; // no exchange
      if (error?.response?.status === 429) return false; // rate limit
      return count < 1;
    },
  });
}

/** Fetch OHLCV candlestick data for a symbol. */
export function useCandles(symbol, interval = "1d", limit = 90) {
  return useQuery({
    queryKey: marketKeys.candles(symbol, interval, limit),
    queryFn: async () => {
      const { data } = await apiClient.get(`/market/${symbol}/candles`, {
        params: { interval, limit },
      });
      return data;
    },
    enabled: !!symbol,
    staleTime: 5 * 60 * 1000, // 5min — candles change slowly
    retry: (count, error) => {
      if (error?.response?.status === 424) return false;
      if (error?.response?.status === 429) return false;
      return count < 1;
    },
  });
}
