import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client";
import type { Application, ApplicationStatus, FollowUp } from "@/lib/types";

export function useApplications() {
  return useQuery({
    queryKey: ["applications"],
    queryFn: () => apiFetch<Application[]>("/applications"),
  });
}

export function useApplicationForJob(jobId: string) {
  return useQuery({
    queryKey: ["applications", "byJob", jobId],
    queryFn: () => apiFetch<Application[]>(`/applications?job_id=${jobId}`),
    enabled: !!jobId,
  });
}

export function useCreateApplication() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: { job_id: string; resume_id?: string }) =>
      apiFetch<Application>("/applications", { method: "POST", body: JSON.stringify(data) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["applications"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useUpdateApplicationStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: ApplicationStatus }) =>
      apiFetch<Application>(`/applications/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["applications"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useUpdateApplication() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & Partial<Pick<Application, "notes" | "followup_opt_out">>) =>
      apiFetch<Application>(`/applications/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["applications"] });
    },
  });
}

export function useApplicationFollowups(applicationId: string | null) {
  return useQuery({
    queryKey: ["applications", applicationId, "followups"],
    queryFn: () => apiFetch<FollowUp[]>(`/applications/${applicationId}/followups`),
    enabled: !!applicationId,
  });
}
