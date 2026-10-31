"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import type { CrawlRun } from "@/lib/types";

export function DiscoverySearch() {
  const [intent, setIntent] = useState("");
  const [force, setForce] = useState(false);
  const client = useQueryClient();
  const { data: runs = [], error } = useQuery({
    queryKey: ["searchHistory"],
    queryFn: () => apiFetch<CrawlRun[]>("/search/history"),
    refetchInterval: 5000,
  });
  const active = runs.find((run) => ["queued", "running", "cancelling"].includes(run.status));
  const lastSuccess = runs.find((run) => run.status === "success");
  const start = useMutation({
    mutationFn: () => apiFetch<CrawlRun>("/search", { method: "POST", body: JSON.stringify({ intent, force }) }),
    onSuccess: () => client.invalidateQueries({ queryKey: ["searchHistory"] }),
  });
  const cancel = useMutation({
    mutationFn: (id: string) => apiFetch(`/search/${id}/cancel`, { method: "POST" }),
    onSuccess: () => client.invalidateQueries({ queryKey: ["searchHistory"] }),
  });
  return <Card className="mb-6 space-y-4">
    <div>
      <h2 className="font-semibold">Discover opportunities</h2>
      <p className="mt-1 text-sm text-zinc-500">Search live sources using your primary CV, portfolio and saved preferences.</p>
    </div>
    <form onSubmit={(event) => { event.preventDefault(); start.mutate(); }} className="space-y-3">
      <textarea aria-label="Describe your job search" value={intent} onChange={(e) => setIntent(e.target.value)} maxLength={2000} rows={3}
        placeholder="Find AI/ML internships in Lahore, Islamabad, Karachi, or remote roles open to applicants in Pakistan, posted in the last seven days."
        className="w-full rounded-lg border border-zinc-300 bg-transparent p-3 text-sm dark:border-zinc-700" />
      <div className="flex flex-wrap items-center gap-3">
        <Button type="submit" disabled={start.isPending || !!active}>{active ? "Search in progress" : start.isPending ? "Queuing…" : "Search live opportunities"}</Button>
        {active && <Button type="button" variant="secondary" disabled={cancel.isPending || active.status === "cancelling"} onClick={() => cancel.mutate(active.id)}>Cancel search</Button>}
        <label className="text-xs text-zinc-500"><input type="checkbox" checked={force} onChange={(e) => setForce(e.target.checked)} /> Retry queries with no recent results</label>
      </div>
    </form>
    {active && <p role="status" className="text-sm text-zinc-600 dark:text-zinc-400">
      {active.status === "queued" ? "Waiting to start — your search begins once background checks for your account pause (usually within two minutes)."
        : active.status === "cancelling" ? "Cancelling after the current source finishes…"
        : `Searching sources · ${active.source_results.length} checked so far · ${active.jobs_found} found`}
    </p>}
    {(error || start.error || cancel.error) && <p role="alert" className="text-sm text-red-600">{(error || start.error || cancel.error)?.message}</p>}
    <p className="text-xs text-zinc-500">{lastSuccess ? `Last successful search: ${new Date(lastSuccess.finished_at ?? lastSuccess.started_at).toLocaleString()}` : "No completed searches yet."} Results refresh automatically. Enrichment and estimated fit scores arrive in background batches.</p>
    <details>
      <summary className="cursor-pointer text-sm font-medium">Search history {active && `· ${active.status}`}</summary>
      <div className="mt-3 space-y-3">
        {runs.slice(0, 10).map((run) => <div key={run.id} className="rounded-lg border border-zinc-200 p-3 text-sm dark:border-zinc-700">
          <p className="font-medium">{run.intent || "Saved profile search"}</p>
          <p className="text-xs text-zinc-500">{run.status} · {run.jobs_found} found · {run.jobs_created} new · {new Date(run.started_at).toLocaleString()}</p>
          {run.error_message && <p className="text-red-600">{run.error_message}</p>}
          {run.source_results.map((source, i) => <p key={i} className="mt-1 text-xs">{source.source}: {source.error || `${source.jobs_found} results`}</p>)}
        </div>)}
      </div>
    </details>
  </Card>;
}

