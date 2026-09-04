/**
 * TanStack Query hooks for exchange management.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import apiClient from "@/lib/api-client";

// ── Query keys ────────────────────────────────────────────────────────────────

export const exchangeKeys = {
  all: ["exchanges"],
  list: () => [...exchangeKeys.all, "list"],
  status: (id) => [...exchangeKeys.all, "status", id],
};

// ── Hooks ─────────────────────────────────────────────────────────────────────

/** Fetch all connected exchanges for the current user. */
export function useExchanges() {
  return useQuery({
    queryKey: exchangeKeys.list(),
    queryFn: async () => {
      const { data } = await apiClient.get("/exchanges");
      return data;
    },
  });
}

/** Fetch status for a single exchange (no live credential check). */
export function useExchangeStatus(exchangeId) {
  return useQuery({
    queryKey: exchangeKeys.status(exchangeId),
    queryFn: async () => {
      const { data } = await apiClient.get(`/exchanges/${exchangeId}/status`);
      return data;
    },
    enabled: !!exchangeId,
  });
}

/** Connect a new exchange account. */
export function useConnectExchange() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ exchange_name, api_key, api_secret, display_label }) => {
      const { data } = await apiClient.post("/exchanges/connect", {
        exchange_name,
        api_key,
        api_secret,
        display_label: display_label || undefined,
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: exchangeKeys.list() });
      toast.success("Exchange connected successfully.");
    },
  });
}

/** Disconnect (soft-delete) an exchange connection. */
export function useDisconnectExchange() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (exchangeId) => {
      await apiClient.delete(`/exchanges/${exchangeId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: exchangeKeys.list() });
      toast.success("Exchange disconnected.");
    },
    onError: () => {
      toast.error("Failed to disconnect exchange. Please try again.");
    },
  });
}

/** Run a live credential validation check for an exchange. */
export function useValidateExchange() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (exchangeId) => {
      const { data } = await apiClient.post(`/exchanges/${exchangeId}/validate`);
      return data;
    },
    onSuccess: (data) => {
      if (data.credential_valid) {
        toast.success("Credentials are valid.");
      } else {
        toast.warning(data.message || "Credentials are invalid.");
      }
      queryClient.invalidateQueries({ queryKey: exchangeKeys.list() });
    },
    onError: () => {
      toast.error("Could not reach exchange. Please try again.");
    },
  });
}
