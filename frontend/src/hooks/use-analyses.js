/**
 * TanStack Query hooks for Saved AI Analyses & Intelligence Reports.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import apiClient from "@/lib/api-client";

// ── Query keys ────────────────────────────────────────────────────────────────

export const analysisKeys = {
  all: ["analyses"],
  list: (filters) => [...analysisKeys.all, "list", filters || {}],
  summary: () => [...analysisKeys.all, "summary"],
  detail: (id) => [...analysisKeys.all, "detail", id],
};

// ── Hooks ─────────────────────────────────────────────────────────────────────

/** Fetch saved analysis reports with optional symbol or assessment filters. */
export function useAnalyses(filters = {}) {
  return useQuery({
    queryKey: analysisKeys.list(filters),
    queryFn: async () => {
      const params = {};
      if (filters.symbol && filters.symbol !== "ALL") {
        params.symbol = filters.symbol;
      }
      if (filters.assessment && filters.assessment !== "ALL") {
        params.assessment = filters.assessment;
      }
      const { data } = await apiClient.get("/analyses", { params });
      return data;
    },
  });
}

/** Fetch summary counts of saved analyses by category. */
export function useAnalysisSummary() {
  return useQuery({
    queryKey: analysisKeys.summary(),
    queryFn: async () => {
      const { data } = await apiClient.get("/analyses/summary");
      return data;
    },
  });
}

/** Fetch single analysis report by UUID. */
export function useAnalysisDetail(analysisId) {
  return useQuery({
    queryKey: analysisKeys.detail(analysisId),
    queryFn: async () => {
      const { data } = await apiClient.get(`/analyses/${analysisId}`);
      return data;
    },
    enabled: Boolean(analysisId),
  });
}

/** Trigger new AI technical analysis report generation. */
export function useGenerateAnalysis() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ symbol, timeframe = "1D", user_notes }) => {
      const { data } = await apiClient.post("/analyses/generate", {
        symbol,
        timeframe,
        user_notes: user_notes || undefined,
      });
      return data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: analysisKeys.all });
      toast.success(`Analysis generated for ${data.symbol}: ${data.assessment}`);
    },
    onError: (error) => {
      const msg = error?.response?.data?.detail || "Failed to generate AI analysis.";
      toast.error(msg);
    },
  });
}

/** Delete a saved analysis report. */
export function useDeleteAnalysis() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (analysisId) => {
      await apiClient.delete(`/analyses/${analysisId}`);
      return analysisId;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: analysisKeys.all });
      toast.success("Analysis report deleted.");
    },
    onError: (error) => {
      const msg = error?.response?.data?.detail || "Failed to delete analysis report.";
      toast.error(msg);
    },
  });
}
