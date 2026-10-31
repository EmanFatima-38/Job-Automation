import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client";
import type { Resume } from "@/lib/types";

export function useResumes() {
  return useQuery({
    queryKey: ["resumes"],
    queryFn: () => apiFetch<Resume[]>("/resumes"),
  });
}

export function useUploadResume() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      return apiFetch<Resume>("/resumes", { method: "POST", body: formData });
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["resumes"] }),
  });
}

export function useSetPrimaryResume() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (resumeId: string) =>
      apiFetch<Resume>(`/resumes/${resumeId}`, {
        method: "PATCH",
        body: JSON.stringify({ is_primary: true }),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["resumes"] }),
  });
}

export function useReparseResume() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (resumeId: string) =>
      apiFetch<Resume>(`/resumes/${resumeId}/reparse`, { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["resumes"] }),
  });
}

export function useDeleteResume() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (resumeId: string) =>
      apiFetch<void>(`/resumes/${resumeId}`, { method: "DELETE" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["resumes"] }),
  });
}
