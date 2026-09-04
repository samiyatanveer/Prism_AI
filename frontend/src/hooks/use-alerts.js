/**
 * TanStack Query hooks for Price and Condition Alerts.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import apiClient from "@/lib/api-client";

// ── Query keys ────────────────────────────────────────────────────────────────

export const alertKeys = {
  all: ["alerts"],
  list: (filter) => [...alertKeys.all, "list", filter || "all"],
  summary: () => [...alertKeys.all, "summary"],
  detail: (id) => [...alertKeys.all, "detail", id],
};

// ── Hooks ─────────────────────────────────────────────────────────────────────

/** Fetch alerts with optional status filter ('active', 'triggered', 'disabled'). */
export function useAlerts(statusFilter) {
  return useQuery({
    queryKey: alertKeys.list(statusFilter),
    queryFn: async () => {
      const params = {};
      if (statusFilter && statusFilter !== "all") {
        params.status = statusFilter;
      }
      const { data } = await apiClient.get("/alerts", { params });
      return data;
    },
    refetchInterval: 15 * 1000, // On-demand refresh live prices every 15s
  });
}

/** Fetch summary counts of alerts (total, active, triggered, disabled). */
export function useAlertSummary() {
  return useQuery({
    queryKey: alertKeys.summary(),
    queryFn: async () => {
      const { data } = await apiClient.get("/alerts/summary");
      return data;
    },
    refetchInterval: 30 * 1000,
  });
}

/** Create a new price alert. */
export function useCreateAlert() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ symbol, target_price, condition, notes }) => {
      const { data } = await apiClient.post("/alerts", {
        symbol,
        target_price,
        condition,
        notes: notes || undefined,
      });
      return data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: alertKeys.all });
      toast.success(`Alert created: ${data.symbol} ${data.condition} $${Number(data.target_price).toLocaleString()}`);
    },
    onError: (error) => {
      const msg = error?.response?.data?.detail || "Failed to create alert.";
      toast.error(msg);
    },
  });
}

/** Update alert threshold, condition, or notes. */
export function useUpdateAlert() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ alertId, target_price, condition, status, notes }) => {
      const { data } = await apiClient.patch(`/alerts/${alertId}`, {
        target_price: target_price || undefined,
        condition: condition || undefined,
        status: status || undefined,
        notes: notes !== undefined ? notes : undefined,
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: alertKeys.all });
      toast.success("Alert updated.");
    },
    onError: (error) => {
      const msg = error?.response?.data?.detail || "Failed to update alert.";
      toast.error(msg);
    },
  });
}

/** Toggle alert active / disabled state. */
export function useToggleAlert() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (alertId) => {
      const { data } = await apiClient.post(`/alerts/${alertId}/toggle`);
      return data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: alertKeys.all });
      toast.success(`Alert is now ${data.status}.`);
    },
    onError: (error) => {
      const msg = error?.response?.data?.detail || "Failed to toggle alert.";
      toast.error(msg);
    },
  });
}

/** Delete an alert. */
export function useDeleteAlert() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (alertId) => {
      await apiClient.delete(`/alerts/${alertId}`);
      return alertId;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: alertKeys.all });
      toast.success("Alert deleted.");
    },
    onError: (error) => {
      const msg = error?.response?.data?.detail || "Failed to delete alert.";
      toast.error(msg);
    },
  });
}
