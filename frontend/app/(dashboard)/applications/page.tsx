"use client";

import {
  Bell,
  BellOff,
  Bookmark,
  Building2,
  Send,
  Star,
  Trophy,
  XCircle,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";

import { Card } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import {
  useApplications,
  useUpdateApplication,
  useUpdateApplicationStatus,
} from "@/hooks/useApplications";
import { useJobs } from "@/hooks/useJobs";
import type { ApplicationStatus } from "@/lib/types";

const COLUMNS: { status: ApplicationStatus; label: string; icon: LucideIcon; tint: string }[] = [
  { status: "saved", label: "Saved", icon: Bookmark, tint: "text-zinc-400" },
  { status: "applied", label: "Applied", icon: Send, tint: "text-blue-500" },
  { status: "interview", label: "Interview", icon: Star, tint: "text-amber-500" },
  { status: "offer", label: "Offer", icon: Trophy, tint: "text-emerald-500" },
  { status: "rejected", label: "Rejected", icon: XCircle, tint: "text-red-500" },
];

export default function ApplicationsPage() {
  const { data: applications } = useApplications();
  const { data: jobs } = useJobs();
  const updateStatus = useUpdateApplicationStatus();
  const updateApplication = useUpdateApplication();

  function jobFor(jobId: string) {
    return jobs?.find((j) => j.id === jobId);
  }

  return (
    <div>
      <h1 className="mb-1 text-2xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
        Applications
      </h1>
      <p className="mb-6 text-sm text-zinc-500 dark:text-zinc-400">
        Track every job from saved to offer.
      </p>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {COLUMNS.map((col) => {
          const colApps = applications?.filter((a) => a.status === col.status) ?? [];
          return (
            <div key={col.status}>
              <div className="mb-3 flex items-center gap-1.5">
                <col.icon className={`h-3.5 w-3.5 ${col.tint}`} />
                <h2 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300">
                  {col.label}
                </h2>
                <span className="text-xs text-zinc-400">{colApps.length}</span>
              </div>
              <div className="space-y-2">
                {colApps.length === 0 && (
                  <div className="rounded-xl border border-dashed border-zinc-200 p-4 text-center text-xs text-zinc-400 dark:border-zinc-800">
                    Nothing here
                  </div>
                )}
                {colApps.map((app) => {
                  const job = jobFor(app.job_id);
                  return (
                    <Card key={app.id} className="p-3">
                      <Link
                        href={`/jobs/${app.job_id}`}
                        className="text-sm font-medium text-zinc-900 hover:text-brand dark:text-zinc-50 dark:hover:text-brand-light"
                      >
                        {job?.title ?? "Job"}
                      </Link>
                      <p className="mt-0.5 flex items-center gap-1 text-xs text-zinc-500 dark:text-zinc-400">
                        <Building2 className="h-3 w-3" />
                        {job?.company ?? "Unknown"}
                      </p>
                      <Select
                        value={app.status}
                        onChange={(e) =>
                          updateStatus.mutate({
                            id: app.id,
                            status: e.target.value as ApplicationStatus,
                          })
                        }
                        className="mt-2 w-full px-2 py-1 text-xs"
                      >
                        {COLUMNS.map((c) => (
                          <option key={c.status} value={c.status}>
                            {c.label}
                          </option>
                        ))}
                      </Select>
                      {app.status === "applied" && (
                        <div className="mt-2 flex items-center justify-between gap-2">
                          {job && !job.contact_email ? (
                            <span className="text-xs text-zinc-400">
                              No contact email - follow-ups unavailable
                            </span>
                          ) : (
                            <span className="text-xs text-zinc-500 dark:text-zinc-400">
                              Followed up {app.followup_count}
                              {app.next_followup_due_at && !app.followup_opt_out
                                ? ` · next ${new Date(app.next_followup_due_at).toLocaleDateString()}`
                                : ""}
                            </span>
                          )}
                          {job?.contact_email && (
                            <button
                              type="button"
                              title={app.followup_opt_out ? "Follow-ups off for this application" : "Follow-ups on - click to opt out"}
                              onClick={() =>
                                updateApplication.mutate({
                                  id: app.id,
                                  followup_opt_out: !app.followup_opt_out,
                                })
                              }
                              className="shrink-0 text-zinc-400 transition-colors hover:text-zinc-700 dark:hover:text-zinc-200"
                            >
                              {app.followup_opt_out ? (
                                <BellOff className="h-3.5 w-3.5" />
                              ) : (
                                <Bell className="h-3.5 w-3.5" />
                              )}
                            </button>
                          )}
                        </div>
                      )}
                    </Card>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
