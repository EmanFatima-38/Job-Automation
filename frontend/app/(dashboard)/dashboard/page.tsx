"use client";

import {
  Bookmark,
  Briefcase,
  RadioTower,
  Send,
  Sparkles,
  Star,
  Trophy,
  XCircle,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { DiscoverySearch } from "@/components/dashboard/DiscoverySearch";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Spinner } from "@/components/ui/spinner";
import { StatCard } from "@/components/dashboard/StatCard";
import { MatchPill } from "@/components/jobs/MatchPill";
import { useCrawlRuns, useTriggerCrawl } from "@/hooks/useCrawl";
import { useDashboardJobs, useDashboardStats } from "@/hooks/useDashboard";
import { useProfile } from "@/hooks/useProfile";
import { ApiError } from "@/lib/api-client";
import { EMPLOYMENT_TYPE_LABELS, WORK_MODE_LABELS } from "@/lib/jobLabels";
import { cn } from "@/lib/utils";

function timeAgo(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.round(diffMs / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.round(mins / 60);
  return `${hours}h ago`;
}

function companyAvatar(name: string | null) {
  const letter = name?.trim()?.[0]?.toUpperCase() ?? "?";
  return (
    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-zinc-100 text-sm font-semibold text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400">
      {letter}
    </div>
  );
}

function CrawlStatusCard() {
  const { data: profile } = useProfile();
  const { data: runs } = useCrawlRuns();
  const triggerCrawl = useTriggerCrawl();
  const [error, setError] = useState<string | null>(null);

  const lastRun = runs?.[0];

  async function handleRunNow() {
    setError(null);
    try {
      await triggerCrawl.mutateAsync();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Crawl failed to run");
    }
  }

  if (!profile?.crawl_enabled) {
    return (
      <Card className="mb-6 flex items-center gap-3 border-dashed">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-zinc-100 text-zinc-400 dark:bg-zinc-800">
          <RadioTower className="h-4 w-4" />
        </div>
        <p className="text-sm text-zinc-500 dark:text-zinc-400">
          Auto-crawl is off.{" "}
          <Link href="/settings" className="font-medium text-brand hover:text-brand-dark dark:text-brand-light">
            Turn it on in Settings
          </Link>{" "}
          to have ApplyPilot search for jobs automatically every hour.
        </p>
      </Card>
    );
  }

  return (
    <Card className="mb-6">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="brand-gradient flex h-9 w-9 items-center justify-center rounded-lg">
            <RadioTower className="h-4 w-4 text-white" />
          </div>
          <h2 className="font-medium text-zinc-900 dark:text-zinc-50">Job crawler</h2>
        </div>
        <Button variant="secondary" onClick={handleRunNow} disabled={triggerCrawl.isPending}>
          {triggerCrawl.isPending && <Spinner className="h-3.5 w-3.5" />}
          {triggerCrawl.isPending ? "Running..." : "Run now"}
        </Button>
      </div>

      {error && <p className="mb-2 text-sm text-red-600 dark:text-red-400">{error}</p>}

      {!lastRun ? (
        <p className="text-sm text-zinc-500 dark:text-zinc-400">
          No crawl runs yet. Click &quot;Run now&quot;.
        </p>
      ) : (
        <div>
          <div className="mb-2 flex flex-wrap items-center gap-2 text-sm">
            <Badge
              status={
                lastRun.status === "success"
                  ? "extracted"
                  : lastRun.status === "failed"
                    ? "failed"
                    : "pending"
              }
            >
              {lastRun.status}
            </Badge>
            <span className="text-zinc-500 dark:text-zinc-400">{timeAgo(lastRun.started_at)}</span>
            <span className="text-zinc-400 dark:text-zinc-500">•</span>
            <span className="text-zinc-500 dark:text-zinc-400">
              {lastRun.jobs_found} found, {lastRun.jobs_created} new
            </span>
          </div>
          <ul className="space-y-1.5 text-xs">
            {lastRun.source_results.map((r, i) => (
              <li key={i} className="flex items-center gap-2">
                <span className="w-20 shrink-0 font-medium capitalize text-zinc-700 dark:text-zinc-300">
                  {r.source}
                </span>
                {r.tier && <span className="shrink-0 text-zinc-400">({r.tier})</span>}
                {r.error ? (
                  <span className="text-red-600 dark:text-red-400">{r.error}</span>
                ) : (
                  <span className="text-emerald-600 dark:text-emerald-400">{r.jobs_found} found</span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}

export default function DashboardPage() {
  const { data: stats } = useDashboardStats();
  const { data: jobs, isLoading: jobsLoading } = useDashboardJobs();
  const [employmentFilter, setEmploymentFilter] = useState("all");
  const [workModeFilter, setWorkModeFilter] = useState("all");
  const [minMatch, setMinMatch] = useState(0);
  const [seniorityFilter, setSeniorityFilter] = useState("");
  const [locationFilter, setLocationFilter] = useState("");
  const [visibility, setVisibility] = useState("recommended");

  const filteredJobs = (jobs ?? [])
    .filter((j) => !seniorityFilter || (j.research?.experience_level ?? "").toLowerCase().includes(seniorityFilter))
    .filter((j) => !locationFilter || `${j.location ?? ""} ${j.research?.remote_eligibility ?? ""}`.toLowerCase().includes(locationFilter.toLowerCase()))
    .filter((j) => visibility === "all" || (visibility === "recommended" && j.research?.recommendation_status === "recommended") || (visibility === "review" && j.research?.recommendation_status === "needs_review") || (visibility === "new" && !j.research?.viewed_at && !j.application_status) || (visibility === "viewed" && !!j.research?.viewed_at) || (visibility === "applied" && j.application_status === "applied") || (visibility === "active" && j.research?.state === "active"))
    .filter((j) => employmentFilter === "all" || j.employment_type === employmentFilter)
    .filter((j) => workModeFilter === "all" || j.work_mode === workModeFilter)
    .filter((j) => minMatch === 0 || (j.match_score ?? -1) >= minMatch)
    .sort((a, b) => (b.match_score ?? -1) - (a.match_score ?? -1));

  const cards = [
    { label: "Saved", value: stats?.saved, icon: Bookmark, color: "zinc" as const },
    { label: "Applied", value: stats?.applied, icon: Send, color: "blue" as const },
    { label: "Interview", value: stats?.interview, icon: Star, color: "amber" as const },
    { label: "Offer", value: stats?.offer, icon: Trophy, color: "emerald" as const },
    { label: "Rejected", value: stats?.rejected, icon: XCircle, color: "red" as const },
  ];

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
            Dashboard
          </h1>
          <p className="mt-0.5 text-sm text-zinc-500 dark:text-zinc-400">
            Your job search, at a glance.
          </p>
        </div>
      </div>

      <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-5">
        {cards.map((c) => (
          <StatCard key={c.label} {...c} />
        ))}
      </div>

      <DiscoverySearch />
      <CrawlStatusCard />

      <Card className="p-0 overflow-hidden">
        {!jobsLoading && !!jobs && (
          <div className="flex flex-wrap items-center gap-2 border-b border-zinc-100 p-4 dark:border-zinc-800">
            <Select value={employmentFilter} onChange={(e) => setEmploymentFilter(e.target.value)}>
              <option value="all">All types</option>
              {Object.entries(EMPLOYMENT_TYPE_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </Select>
            <Select value={workModeFilter} onChange={(e) => setWorkModeFilter(e.target.value)}>
              <option value="all">All locations</option>
              {Object.entries(WORK_MODE_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </Select>
            <Select value={minMatch} onChange={(e) => setMinMatch(Number(e.target.value))}>
              <option value={0}>Any match</option>
              <option value={50}>50+ fit score</option>
              <option value={70}>70+ fit score</option>
              <option value={90}>90+ fit score</option>
            </Select>
            <Select value={seniorityFilter} onChange={(e) => setSeniorityFilter(e.target.value)}><option value="">All seniorities</option><option value="intern">Intern</option><option value="entry">Entry level</option><option value="junior">Junior</option><option value="senior">Senior</option></Select>
            <input aria-label="Filter location or remote eligibility" value={locationFilter} onChange={(e) => setLocationFilter(e.target.value)} placeholder="City or eligible country" className="rounded-md border bg-transparent p-2 text-sm" />
            <Select value={visibility} onChange={(e) => setVisibility(e.target.value)}><option value="recommended">Verified recommendations</option><option value="review">Needs review</option><option value="all">All opportunities</option><option value="new">Not viewed or applied</option><option value="viewed">Viewed</option><option value="applied">Applied</option><option value="active">Active</option></Select>
            {!!jobs.length && (
              <span className="ml-auto text-xs text-zinc-400">
                {filteredJobs.length} of {jobs.length} jobs
              </span>
            )}
          </div>
        )}

        {jobsLoading ? (
          <div className="space-y-4 p-6">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="flex items-center gap-3">
                <Skeleton className="h-9 w-9 rounded-lg" />
                <div className="flex-1 space-y-2">
                  <Skeleton className="h-3.5 w-1/3" />
                  <Skeleton className="h-3 w-1/4" />
                </div>
              </div>
            ))}
          </div>
        ) : !jobs?.length ? (
          <div className="flex flex-col items-center gap-3 p-12 text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-zinc-100 dark:bg-zinc-800">
              <Briefcase className="h-5 w-5 text-zinc-400" />
            </div>
            <p className="text-sm text-zinc-500 dark:text-zinc-400">
              No jobs yet.{" "}
              <Link href="/jobs/new" className="font-medium text-brand hover:text-brand-dark dark:text-brand-light">
                Add your first job
              </Link>{" "}
              or turn on auto-crawl in Settings.
            </p>
          </div>
        ) : !filteredJobs.length ? (
          <div className="flex flex-col items-center gap-2 p-12 text-center">
            <Sparkles className="h-5 w-5 text-zinc-400" />
            <p className="text-sm text-zinc-500 dark:text-zinc-400">{visibility === "recommended" ? "No verified recommendations yet. Check Needs review for leads and outstanding checks." : "No jobs match these filters."}</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="text-xs uppercase tracking-wide text-zinc-400 dark:text-zinc-500">
                  <th className="px-4 pb-2 pt-4 font-medium">Job</th>
                  <th className="px-4 pb-2 pt-4 font-medium">Type</th>
                  <th className="px-4 pb-2 pt-4 font-medium">Match</th>
                  <th className="px-4 pb-2 pt-4 font-medium">Status</th>
                  <th className="px-4 pb-2 pt-4 font-medium"></th>
                </tr>
              </thead>
              <tbody>
                {filteredJobs.map((row) => (
                  <tr
                    key={row.job_id}
                    className="group border-t border-zinc-100 transition-colors hover:bg-zinc-50/80 dark:border-zinc-800 dark:hover:bg-zinc-800/40"
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        {companyAvatar(row.company)}
                        <div className="min-w-0">
                          <p className="truncate font-medium text-zinc-900 dark:text-zinc-50">
                            {row.title ?? "Untitled"}
                          </p>
                          <p className="truncate text-xs text-zinc-500 dark:text-zinc-400">
                            {row.company ?? "Unknown company"}
                            {row.research && <span className="ml-2">· {row.research.state ?? "unknown"} · {row.research.posted_at ? `Posted ${row.research.posted_at.slice(0, 10)}` : "Posting date unknown"}</span>}
                          </p>
                          {!!row.research?.recommendation_reasons?.length && <p className="mt-1 max-w-lg text-xs text-amber-700 dark:text-amber-400">{row.research.recommendation_reasons.join(" · ")}</p>}
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-xs text-zinc-500 dark:text-zinc-400">
                      {[
                        row.employment_type ? EMPLOYMENT_TYPE_LABELS[row.employment_type] : null,
                        row.work_mode ? WORK_MODE_LABELS[row.work_mode] : null,
                      ]
                        .filter(Boolean)
                        .join(" · ") || "—"}
                    </td>
                    <td className="px-4 py-3">
                      <MatchPill score={row.match_score} />
                    </td>
                    <td className="px-4 py-3">
                      {row.application_status ? (
                        <Badge status={row.application_status}>{row.application_status}</Badge>
                      ) : (
                        <Badge status={row.extraction_status}>{row.extraction_status}</Badge>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Link
                        href={`/jobs/${row.job_id}`}
                        className={cn(
                          "text-xs font-medium text-zinc-400 transition-colors group-hover:text-brand dark:group-hover:text-brand-light"
                        )}
                      >
                        View →
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}

