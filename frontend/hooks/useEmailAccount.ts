import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError, apiFetch } from "@/lib/api-client";
import type { EmailAccount, EmailAccountInput, EmailTestResult } from "@/lib/types";

export function useEmailAccount() {
  return useQuery({
    queryKey: ["emailAccount"],
    queryFn: async () => {
      try {
        return await apiFetch<EmailAccount>("/email-account");
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) return null;
        throw err;
      }
    },
  });
}

export function useSaveEmailAccount() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: EmailAccountInput) =>
      apiFetch<EmailAccount>("/email-account", { method: "PUT", body: JSON.stringify(data) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["emailAccount"] }),
  });
}

export function useDeleteEmailAccount() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => apiFetch<void>("/email-account", { method: "DELETE" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["emailAccount"] }),
  });
}

export function useTestEmailAccount() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => apiFetch<EmailTestResult>("/email-account/test", { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["emailAccount"] }),
  });
}
