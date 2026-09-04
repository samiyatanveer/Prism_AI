/**
 * TanStack Query hooks for Watchlist management.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import apiClient from "@/lib/api-client";

// ── Query keys ────────────────────────────────────────────────────────────────

export const watchlistKeys = {
  all: ["watchlists"],
  list: () => [...watchlistKeys.all, "list"],
  detail: (id) => [...watchlistKeys.all, "detail", id],
};

// ── Hooks ─────────────────────────────────────────────────────────────────────

/** Fetch all watchlists for the current user. */
export function useWatchlists() {
  return useQuery({
    queryKey: watchlistKeys.list(),
    queryFn: async () => {
      const { data } = await apiClient.get("/watchlists");
      return data;
    },
  });
}

/** Fetch a single watchlist detail with items and real-time market data enrichment. */
export function useWatchlist(watchlistId) {
  return useQuery({
    queryKey: watchlistKeys.detail(watchlistId),
    queryFn: async () => {
      const { data } = await apiClient.get(`/watchlists/${watchlistId}`);
      return data;
    },
    enabled: !!watchlistId,
    refetchInterval: 15 * 1000, // Refresh live quotes every 15 seconds
  });
}

/** Create a new watchlist. */
export function useCreateWatchlist() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ name, description, symbols }) => {
      const { data } = await apiClient.post("/watchlists", {
        name,
        description: description || undefined,
        symbols: symbols && symbols.length > 0 ? symbols : undefined,
      });
      return data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: watchlistKeys.list() });
      toast.success(`Watchlist "${data.name}" created.`);
    },
    onError: (error) => {
      const msg = error?.response?.data?.detail || "Failed to create watchlist.";
      toast.error(msg);
    },
  });
}

/** Update watchlist name or description. */
export function useUpdateWatchlist() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ watchlistId, name, description }) => {
      const { data } = await apiClient.patch(`/watchlists/${watchlistId}`, {
        name: name || undefined,
        description: description !== undefined ? description : undefined,
      });
      return data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: watchlistKeys.list() });
      queryClient.invalidateQueries({ queryKey: watchlistKeys.detail(data.id) });
      toast.success("Watchlist updated.");
    },
    onError: (error) => {
      const msg = error?.response?.data?.detail || "Failed to update watchlist.";
      toast.error(msg);
    },
  });
}

/** Delete a watchlist. */
export function useDeleteWatchlist() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (watchlistId) => {
      await apiClient.delete(`/watchlists/${watchlistId}`);
      return watchlistId;
    },
    onSuccess: (deletedId) => {
      queryClient.invalidateQueries({ queryKey: watchlistKeys.list() });
      queryClient.removeQueries({ queryKey: watchlistKeys.detail(deletedId) });
      toast.success("Watchlist deleted.");
    },
    onError: (error) => {
      const msg = error?.response?.data?.detail || "Failed to delete watchlist.";
      toast.error(msg);
    },
  });
}

/** Add a symbol item to a watchlist. */
export function useAddWatchlistItem(watchlistId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ symbol, notes }) => {
      const { data } = await apiClient.post(`/watchlists/${watchlistId}/items`, {
        symbol,
        notes: notes || undefined,
      });
      return data;
    },
    onSuccess: (item) => {
      queryClient.invalidateQueries({ queryKey: watchlistKeys.detail(watchlistId) });
      queryClient.invalidateQueries({ queryKey: watchlistKeys.list() });
      toast.success(`Added ${item.symbol} to watchlist.`);
    },
    onError: (error) => {
      const msg = error?.response?.data?.detail || "Failed to add asset to watchlist.";
      toast.error(msg);
    },
  });
}

/** Remove a symbol item from a watchlist. */
export function useRemoveWatchlistItem(watchlistId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (itemId) => {
      await apiClient.delete(`/watchlists/${watchlistId}/items/${itemId}`);
      return itemId;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: watchlistKeys.detail(watchlistId) });
      queryClient.invalidateQueries({ queryKey: watchlistKeys.list() });
      toast.success("Removed asset from watchlist.");
    },
    onError: (error) => {
      const msg = error?.response?.data?.detail || "Failed to remove asset.";
      toast.error(msg);
    },
  });
}
