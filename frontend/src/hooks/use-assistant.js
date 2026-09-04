/**
 * TanStack Query hooks for AI Assistant chat and sessions.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import apiClient from "@/lib/api-client";

export const assistantKeys = {
  all: ["assistant"],
  sessions: () => [...assistantKeys.all, "sessions"],
  session: (id) => [...assistantKeys.all, "session", id],
};

/** Fetch all chat sessions for the current user. */
export function useSessions() {
  return useQuery({
    queryKey: assistantKeys.sessions(),
    queryFn: async () => {
      const { data } = await apiClient.get("/assistant/sessions");
      return data;
    },
    staleTime: 30 * 1000,
  });
}

/** Fetch full message history for a single chat session. */
export function useSession(sessionId) {
  return useQuery({
    queryKey: assistantKeys.session(sessionId),
    queryFn: async () => {
      const { data } = await apiClient.get(`/assistant/sessions/${sessionId}`);
      return data;
    },
    enabled: !!sessionId,
    staleTime: 60 * 1000,
  });
}

/** Send a message to the AI assistant. */
export function useSendMessage() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ message, sessionId }) => {
      const { data } = await apiClient.post("/assistant/chat", {
        message,
        session_id: sessionId || null,
      });
      return data;
    },
    onSuccess: (data) => {
      // Invalidate session list and specific session query to refresh history
      queryClient.invalidateQueries({ queryKey: assistantKeys.sessions() });
      if (data.session_id) {
        queryClient.invalidateQueries({
          queryKey: assistantKeys.session(data.session_id),
        });
      }
    },
    onError: (error) => {
      const status = error?.response?.status;
      const detail = error?.response?.data?.detail;

      if (status === 503) {
        toast.error("AI Assistant is currently unavailable.", {
          description: detail || "Please verify backend GROQ configuration.",
        });
      } else if (status === 401) {
        toast.error("Authentication expired. Please log in again.");
      }
    },
  });
}
