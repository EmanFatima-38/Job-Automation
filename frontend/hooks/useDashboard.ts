import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client";
import type { DashboardJobRow, DashboardStats } from "@/lib/types";

export function useDashboardStats() {
  return useQuery({
    queryKey: ["dashboard", "stats"],
    queryFn: () => apiFetch<DashboardStats>("/dashboard/stats"),
  });
}

export function useDashboardJobs() {
  return useQuery({
    queryKey: ["dashboard", "jobs"],
    refetchInterval: 10000,
    queryFn: () => apiFetch<DashboardJobRow[]>("/dashboard/jobs"),
  });
}
