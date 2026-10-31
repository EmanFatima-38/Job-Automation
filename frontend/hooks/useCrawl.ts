import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client";
import type { CrawlRun } from "@/lib/types";

export function useCrawlRuns() {
  return useQuery({
    queryKey: ["crawlRuns"],
    refetchInterval: 10000,
    queryFn: () => apiFetch<CrawlRun[]>("/crawl/runs"),
  });
}

export function useTriggerCrawl() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => apiFetch<CrawlRun>("/crawl/run", { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["crawlRuns"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });
}
