"use client";

import {
  Bookmark,
  Building2,
  CheckCircle2,
  DollarSign,
  ExternalLink,
  FileText,
  ListChecks,
  Mail,
  MapPin,
  Newspaper,
  RotateCw,
  Send,
  Target,
} from "lucide-react";
import Link from "next/link";
import { use, useState, useEffect } from "react";
import { apiFetch } from "@/lib/api-client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Spinner } from "@/components/ui/spinner";
import { MatchPill } from "@/components/jobs/MatchPill";
import {
  useApplicationForJob,
  useApplicationFollowups,
  useCreateApplication,
  useUpdateApplicationStatus,
} from "@/hooks/useApplications";
import {
  useComputeMatch,
  useGenerateDocument,
  useJob,
  useJobDocuments,
  useJobMatch,
  useReextractJob,
} from "@/hooks/useJobs";
import { useResumes } from "@/hooks/useResumes";
import { ApiError } from "@/lib/api-client";
import type { Job } from "@/lib/types";
import { EMPLOYMENT_TYPE_LABELS, WORK_MODE_LABELS } from "@/lib/jobLabels";

function buildMailtoHref(job: Job, coverLetterContent: string): string {
  const subject = `Application for ${job.title ?? "the position"}${job.company ? ` at ${job.company}` : ""}`;
  const params = new URLSearchParams({ subject, body: coverLetterContent });
  return `mailto:${job.contact_email ?? ""}?${params.toString()}`;
}

export default function JobDetailPage({ params }: { params: Promise<{ jobId: string }> }) {
  const { jobId } = use(params);
  const { data: job, isLoading } = useJob(jobId);
  const { data: resumes } = useResumes();
  const [resumeId, setResumeId] = useState<string>("");
  const [actionError, setActionError] = useState<string | null>(null);
  const [tracked, setTracked] = useState(false);

  const computeMatch = useComputeMatch(jobId);
  const { data: documents } = useJobDocuments(jobId);
  const generateDocument = useGenerateDocument(jobId);
  const createApplication = useCreateApplication();
  const { data: existingApplications } = useApplicationForJob(jobId);
  const updateStatus = useUpdateApplicationStatus();
  const reextractJob = useReextractJob(jobId);

  const existingApplication = existingApplications?.[0];
  const applicationId = existingApplication?.id ?? createApplication.data?.id ?? null;
  const isApplied = existingApplication?.status === "applied";
  const { data: followups } = useApplicationFollowups(isApplied ? applicationId : null);

  useEffect(() => { void apiFetch(`/jobs/${jobId}/viewed`, { method: "POST" }).catch(() => {}); }, [jobId]);
  const effectiveResumeId = resumeId || resumes?.find((r) => r.is_primary)?.id || resumes?.[0]?.id || "";
  const { data: match } = useJobMatch(jobId, effectiveResumeId || null);

  async function runAction(fn: () => Promise<unknown>) {
    setActionError(null);
    try {
      await fn();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Something went wrong");
    }
  }

  if (isLoading || !job) {
    return (
      <div className="max-w-3xl space-y-6">
        <Skeleton className="h-8 w-2/3" />
        <Skeleton className="h-4 w-1/3" />
        <Card className="space-y-3">
          <Skeleton className="h-4 w-1/4" />
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-5/6" />
        </Card>
      </div>
    );
  }

  const notReady = job.extraction_status !== "extracted";

  return (
    <div className="max-w-3xl space-y-6">
      <Link
        href="/dashboard"
        className="text-sm text-zinc-500 transition-colors hover:text-zinc-900 dark:hover:text-zinc-100"
      >
        ← Back to dashboard
      </Link>

      <div>
        <div className="flex flex-wrap items-center gap-2.5">
          <h1 className="text-2xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
            {job.title ?? "Untitled job"}
          </h1>
          <Badge status={job.extraction_status}>{job.extraction_status}</Badge>
        </div>

        <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-sm text-zinc-500 dark:text-zinc-400">
          <span className="flex items-center gap-1.5">
            <Building2 className="h-3.5 w-3.5" />
            {job.company ?? "Unknown company"}
          </span>
          {job.location && (
            <span className="flex items-center gap-1.5">
              <MapPin className="h-3.5 w-3.5" />
              {job.location}
            </span>
          )}
          {job.salary_range && (
            <span className="flex items-center gap-1.5">
              <DollarSign className="h-3.5 w-3.5" />
              {job.salary_range}
            </span>
          )}
          {job.source_url && (
            <a
              href={job.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 font-medium text-brand hover:text-brand-dark dark:text-brand-light"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              View original posting
            </a>
          )}
        </div>

        {(job.employment_type || job.work_mode) && (
          <div className="mt-3 flex gap-2">
            {job.employment_type && (
              <Badge status="pending" icon={false}>
                {EMPLOYMENT_TYPE_LABELS[job.employment_type] ?? job.employment_type}
              </Badge>
            )}
            {job.work_mode && (
              <Badge status="pending" icon={false}>
                {WORK_MODE_LABELS[job.work_mode] ?? job.work_mode}
              </Badge>
            )}
          </div>
        )}

        {job.extraction_error && (
          <div className="mt-4 flex items-start gap-3 rounded-lg bg-red-50 p-3 dark:bg-red-950/30">
            <p className="flex-1 text-sm text-red-600 dark:text-red-400">{job.extraction_error}</p>
            <Button
              variant="secondary"
              onClick={() => runAction(() => reextractJob.mutateAsync())}
              disabled={reextractJob.isPending}
            >
              <RotateCw className="h-3.5 w-3.5" />
              {reextractJob.isPending ? "Retrying..." : "Retry"}
            </Button>
          </div>
        )}
      </div>

      {job.extraction_status === "extracted" && !!job.requirements?.length && (
        <Card>
          <h2 className="mb-3 flex items-center gap-2 font-medium text-zinc-900 dark:text-zinc-50">
            <ListChecks className="h-4 w-4 text-zinc-400" />
            Requirements
          </h2>
          <ul className="space-y-2">
            {job.requirements.map((r) => (
              <li key={r} className="flex items-start gap-2 text-sm text-zinc-600 dark:text-zinc-400">
                <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-zinc-300 dark:text-zinc-600" />
                {r}
              </li>
            ))}
          </ul>
        </Card>
      )}

      {job.research && <Card className="space-y-2 text-sm">
        <p className="font-medium">{job.research.recommendation_status === "recommended" ? "Verified recommendation" : job.research.recommendation_status === "excluded" ? "Excluded from recommendations" : "Needs review"}</p>
        <p>Status: {job.research.state ?? "unknown"} · Verification: {job.research.verification_status ?? "unverified"}</p>
        <p>Posted: {job.research.posted_at ?? "Unknown"} · Deadline: {job.research.deadline ?? "Unknown"}</p>
        <p>Remote eligibility: {job.research.remote_eligibility ?? "Unknown"}</p>
        {[...(job.research.exclusion_reasons ?? []), ...(job.research.eligibility_concerns ?? [])].map((concern) => <p key={concern} className="text-amber-700 dark:text-amber-400">{concern}</p>)}
        {job.research.application_url && <a href={job.research.application_url} target="_blank" rel="noopener noreferrer" className="text-brand">Open application page ↗</a>}
      </Card>}
      {job.raw_input_text && (
        <Card>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="flex items-center gap-2 font-medium text-zinc-900 dark:text-zinc-50">
              <Newspaper className="h-4 w-4 text-zinc-400" />
              Full job posting
            </h2>
            {job.source_url && (
              <a
                href={job.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-xs font-medium text-brand hover:text-brand-dark dark:text-brand-light"
              >
                Open original
                <ExternalLink className="h-3 w-3" />
              </a>
            )}
          </div>
          <p className="mb-3 text-xs text-zinc-400 dark:text-zinc-500">
            Exactly as fetched from the source - unedited.
          </p>
          <div className="whitespace-pre-wrap rounded-lg bg-zinc-50 p-4 text-sm leading-relaxed text-zinc-700 dark:bg-zinc-800/50 dark:text-zinc-300">
            {job.raw_input_text}
          </div>
        </Card>
      )}

      <Card>
        <h2 className="mb-4 font-medium text-zinc-900 dark:text-zinc-50">Match &amp; generate</h2>

        {!resumes?.length ? (
          <p className="text-sm text-zinc-500 dark:text-zinc-400">
            Upload a resume first to compute a match or generate documents.
          </p>
        ) : (
          <div className="space-y-5">
            <Select
              value={effectiveResumeId}
              onChange={(e) => setResumeId(e.target.value)}
              className="w-full"
            >
              {resumes.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.original_filename}
                </option>
              ))}
            </Select>

            <div className="flex flex-wrap gap-2">
              <Button
                variant="secondary"
                disabled={computeMatch.isPending || notReady}
                onClick={() => runAction(() => computeMatch.mutateAsync(effectiveResumeId))}
              >
                {computeMatch.isPending ? <Spinner className="h-3.5 w-3.5" /> : <Target className="h-3.5 w-3.5" />}
                {computeMatch.isPending ? "Scoring..." : "Compute match"}
              </Button>
              <Button
                variant="secondary"
                disabled={generateDocument.isPending || notReady}
                onClick={() =>
                  runAction(() =>
                    generateDocument.mutateAsync({
                      resume_id: effectiveResumeId,
                      doc_type: "cover_letter",
                    })
                  )
                }
              >
                <Mail className="h-3.5 w-3.5" />
                Cover letter
              </Button>
              <Button
                variant="secondary"
                disabled={generateDocument.isPending || notReady}
                onClick={() =>
                  runAction(() =>
                    generateDocument.mutateAsync({
                      resume_id: effectiveResumeId,
                      doc_type: "resume_bullets",
                    })
                  )
                }
              >
                <ListChecks className="h-3.5 w-3.5" />
                Resume bullets
              </Button>
              <Button
                onClick={() =>
                  runAction(() => createApplication.mutateAsync({ job_id: jobId })).then(() =>
                    setTracked(true)
                  )
                }
                disabled={createApplication.isPending || tracked || !!existingApplication}
              >
                <Bookmark className="h-3.5 w-3.5" />
                {tracked || existingApplication ? "Tracked" : "Track application"}
              </Button>
              {applicationId && !isApplied && (
                <Button
                  variant="secondary"
                  onClick={() =>
                    runAction(() =>
                      updateStatus.mutateAsync({ id: applicationId, status: "applied" })
                    )
                  }
                  disabled={updateStatus.isPending}
                >
                  <Send className="h-3.5 w-3.5" />
                  {updateStatus.isPending ? "Marking..." : "Mark as applied"}
                </Button>
              )}
            </div>

            {actionError && (
              <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600 dark:bg-red-950/40 dark:text-red-400">
                {actionError}
              </p>
            )}

            {match && (
              <div className="rounded-xl border border-zinc-200 p-4 dark:border-zinc-800">
                <div className="mb-2 flex items-center gap-3">
                  <MatchPill score={match.match_score} />
                  <span className="text-sm font-medium text-zinc-500 dark:text-zinc-400">match</span>
                </div>
                <p className="text-sm text-zinc-600 dark:text-zinc-400">{match.rationale}</p>
                <p className="mt-2 text-xs text-zinc-500">Estimated fit, not a hiring probability.</p>
                {match.details?.relevant_projects?.map((project) => <p key={project} className="mt-2 text-sm">Relevant project: {project}</p>)}
                {match.details?.eligibility_concerns?.map((concern) => <p key={concern} className="mt-2 text-sm text-amber-700 dark:text-amber-400">{concern}</p>)}
                {!!match.matched_skills.length && (
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {match.matched_skills.map((s) => (
                      <span
                        key={s}
                        className="rounded-full bg-emerald-50 px-2 py-0.5 text-xs text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300"
                      >
                        {s}
                      </span>
                    ))}
                  </div>
                )}
                {!!match.missing_skills.length && (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {match.missing_skills.map((s) => (
                      <span
                        key={s}
                        className="rounded-full bg-zinc-100 px-2 py-0.5 text-xs text-zinc-500 line-through decoration-zinc-400 dark:bg-zinc-800 dark:text-zinc-400"
                      >
                        {s}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}

            {documents?.map((doc) => (
              <div key={doc.id} className="rounded-xl border border-zinc-200 p-4 dark:border-zinc-800">
                <div className="mb-2 flex items-center justify-between">
                  <p className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-zinc-400">
                    <FileText className="h-3.5 w-3.5" />
                    {doc.doc_type.replace("_", " ")}
                  </p>
                  {doc.doc_type === "cover_letter" && (
                    <a
                      href={buildMailtoHref(job, doc.content)}
                      title={
                        job.contact_email
                          ? `Opens your mail app addressed to ${job.contact_email}`
                          : "No company email found on this posting - opens your mail app, add the recipient yourself"
                      }
                      className="flex items-center gap-1 rounded-md bg-brand/[0.08] px-2 py-1 text-xs font-medium text-brand hover:bg-brand/[0.15] dark:text-brand-light"
                    >
                      <Send className="h-3 w-3" />
                      Email this
                    </a>
                  )}
                </div>
                <pre className="whitespace-pre-wrap font-sans text-sm text-zinc-700 dark:text-zinc-300">
                  {doc.content}
                </pre>
              </div>
            ))}

            {isApplied && !!followups?.length && (
              <div className="rounded-xl border border-zinc-200 p-4 dark:border-zinc-800">
                <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-zinc-400">
                  <Send className="h-3.5 w-3.5" />
                  Follow-up history
                </p>
                <ul className="space-y-2">
                  {followups.map((f) => (
                    <li key={f.id} className="flex items-center justify-between gap-2 text-sm">
                      <span className="truncate text-zinc-700 dark:text-zinc-300">{f.subject}</span>
                      <span className="flex items-center gap-2 shrink-0">
                        <span className="text-xs text-zinc-400">
                          {new Date(f.sent_at).toLocaleDateString()}
                        </span>
                        <Badge status={f.status === "sent" ? "extracted" : "failed"}>{f.status}</Badge>
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </Card>
    </div>
  );
}
