/**
 * TanStack Query hooks for Support Complaints and Tickets Portal.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import apiClient from "@/lib/api-client";

// ── Query keys ────────────────────────────────────────────────────────────────

export const complaintKeys = {
  all: ["complaints"],
  list: (filters) => [...complaintKeys.all, "list", filters || {}],
  summary: () => [...complaintKeys.all, "summary"],
  detail: (id) => [...complaintKeys.all, "detail", id],
};

// ── Hooks ─────────────────────────────────────────────────────────────────────

/** Fetch user's complaints with optional status and category filters. */
export function useComplaints(filters = {}) {
  return useQuery({
    queryKey: complaintKeys.list(filters),
    queryFn: async () => {
      const params = {};
      if (filters.status && filters.status !== "all") {
        params.status = filters.status;
      }
      if (filters.category && filters.category !== "all") {
        params.category = filters.category;
      }
      const { data } = await apiClient.get("/complaints", { params });
      return data;
    },
    refetchInterval: 30 * 1000,
  });
}

/** Fetch complaint status summary counts. */
export function useComplaintSummary() {
  return useQuery({
    queryKey: complaintKeys.summary(),
    queryFn: async () => {
      const { data } = await apiClient.get("/complaints/summary");
      return data;
    },
  });
}

/** Fetch single complaint with full conversation thread. */
export function useComplaintDetail(complaintId) {
  return useQuery({
    queryKey: complaintKeys.detail(complaintId),
    queryFn: async () => {
      const { data } = await apiClient.get(`/complaints/${complaintId}`);
      return data;
    },
    enabled: Boolean(complaintId),
    refetchInterval: 15 * 1000,
  });
}

/** Submit a new complaint or support ticket. */
export function useCreateComplaint() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ subject, category, priority, description }) => {
      const { data } = await apiClient.post("/complaints", {
        subject,
        category,
        priority,
        description,
      });
      return data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: complaintKeys.all });
      toast.success(`Support ticket created: #${data.id.slice(0, 8)}`);
    },
    onError: (error) => {
      const msg = error?.response?.data?.detail || "Failed to submit ticket.";
      toast.error(msg);
    },
  });
}

/** Post a reply message to a complaint thread. */
export function useAddComplaintMessage() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ complaintId, message }) => {
      const { data } = await apiClient.post(`/complaints/${complaintId}/messages`, {
        message,
      });
      return data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: complaintKeys.detail(data.id) });
      queryClient.invalidateQueries({ queryKey: complaintKeys.all });
      toast.success("Message sent.");
    },
    onError: (error) => {
      const msg = error?.response?.data?.detail || "Failed to send message.";
      toast.error(msg);
    },
  });
}

/** Update complaint status or resolution notes. */
export function useUpdateComplaintStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ complaintId, status, resolution_notes }) => {
      const { data } = await apiClient.patch(`/complaints/${complaintId}/status`, {
        status,
        resolution_notes: resolution_notes || undefined,
      });
      return data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: complaintKeys.detail(data.id) });
      queryClient.invalidateQueries({ queryKey: complaintKeys.all });
      toast.success(`Ticket status updated to ${data.status}.`);
    },
    onError: (error) => {
      const msg = error?.response?.data?.detail || "Failed to update ticket status.";
      toast.error(msg);
    },
  });
}
