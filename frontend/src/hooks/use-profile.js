"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import apiClient from "@/lib/api-client";

const profileKey = ["profile"];

export function useProfile() {
  return useQuery({
    queryKey: profileKey,
    queryFn: async () => (await apiClient.get("/profile")).data,
  });
}

export function useSecuritySessions() {
  return useQuery({
    queryKey: [...profileKey, "sessions"],
    queryFn: async () => (await apiClient.get("/profile/sessions")).data,
  });
}

export function useUpdateProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload) => (await apiClient.patch("/profile", payload)).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: profileKey }),
  });
}

export function useRevokeSecuritySession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id) => apiClient.delete(`/profile/sessions/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [...profileKey, "sessions"] }),
  });
}
