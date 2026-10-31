import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client";
import type { GeneratedDocument, Job, Match } from "@/lib/types";

export function useJobs() {
  return useQuery({
    queryKey: ["jobs"],
    queryFn: () => apiFetch<Job[]>("/jobs"),
  });
}

export function useJob(jobId: string) {
  return useQuery({
    queryKey: ["jobs", jobId],
    queryFn: () => apiFetch<Job>(`/jobs/${jobId}`),
    enabled: !!jobId,
  });
}

interface CreateJobInput {
  source_type: "url" | "text";
  source_url?: string;
  raw_text?: string;
}

export function useCreateJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateJobInput) =>
      apiFetch<Job>("/jobs", { method: "POST", body: JSON.stringify(data) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["jobs"] }),
  });
}

export function useReextractJob(jobId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => apiFetch<Job>(`/jobs/${jobId}/reextract`, { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs", jobId] });
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });
}

export function useComputeMatch(jobId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (resumeId: string) =>
      apiFetch<Match>(`/jobs/${jobId}/match?resume_id=${resumeId}`, { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs", jobId, "match"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard", "jobs"] });
    },
  });
}

export function useJobMatch(jobId: string, resumeId: string | null) {
  return useQuery({
    queryKey: ["jobs", jobId, "match", resumeId],
    queryFn: () => apiFetch<Match>(`/jobs/${jobId}/match?resume_id=${resumeId}`),
    enabled: !!jobId && !!resumeId,
    retry: false,
  });
}

export function useJobDocuments(jobId: string) {
  return useQuery({
    queryKey: ["jobs", jobId, "documents"],
    queryFn: () => apiFetch<GeneratedDocument[]>(`/jobs/${jobId}/documents`),
    enabled: !!jobId,
  });
}

export function useGenerateDocument(jobId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: { resume_id: string; doc_type: "cover_letter" | "resume_bullets" }) =>
      apiFetch<GeneratedDocument>(`/jobs/${jobId}/documents`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["jobs", jobId, "documents"] }),
  });
}
