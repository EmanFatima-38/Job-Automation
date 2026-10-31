"use client";

import { Link2, Sparkles, Type } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { useCreateJob } from "@/hooks/useJobs";
import { ApiError } from "@/lib/api-client";
import { cn } from "@/lib/utils";

export default function NewJobPage() {
  const router = useRouter();
  const createJob = useCreateJob();
  const [mode, setMode] = useState<"text" | "url">("text");
  const [rawText, setRawText] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const job =
        mode === "text"
          ? await createJob.mutateAsync({ source_type: "text", raw_text: rawText })
          : await createJob.mutateAsync({ source_type: "url", source_url: sourceUrl });
      router.push(`/jobs/${job.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not add this job");
    }
  }

  return (
    <div className="max-w-2xl">
      <h1 className="mb-1 text-2xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
        Add a job
      </h1>
      <p className="mb-6 text-sm text-zinc-500 dark:text-zinc-400">
        Paste a posting and ApplyPilot will extract the details and score it against your resume.
      </p>
      <Card>
        <div className="mb-4 inline-flex rounded-lg bg-zinc-100 p-1 dark:bg-zinc-800">
          <button
            type="button"
            onClick={() => setMode("text")}
            className={cn(
              "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-all",
              mode === "text"
                ? "bg-white text-zinc-900 shadow-sm dark:bg-zinc-700 dark:text-zinc-50"
                : "text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200"
            )}
          >
            <Type className="h-3.5 w-3.5" />
            Paste text
          </button>
          <button
            type="button"
            onClick={() => setMode("url")}
            className={cn(
              "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-all",
              mode === "url"
                ? "bg-white text-zinc-900 shadow-sm dark:bg-zinc-700 dark:text-zinc-50"
                : "text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200"
            )}
          >
            <Link2 className="h-3.5 w-3.5" />
            Paste URL
          </button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          {mode === "text" ? (
            <textarea
              value={rawText}
              onChange={(e) => setRawText(e.target.value)}
              placeholder="Paste the full job description here..."
              rows={12}
              required
              className="w-full rounded-lg border border-zinc-300 bg-white px-3.5 py-2.5 text-sm text-zinc-900 shadow-sm transition-colors placeholder:text-zinc-400 focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/20 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-50 dark:placeholder:text-zinc-500"
            />
          ) : (
            <Input
              type="url"
              value={sourceUrl}
              onChange={(e) => setSourceUrl(e.target.value)}
              placeholder="https://company.com/careers/job-123"
              required
            />
          )}
          {error && (
            <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600 dark:bg-red-950/40 dark:text-red-400">
              {error}
            </p>
          )}
          <Button type="submit" disabled={createJob.isPending}>
            {createJob.isPending ? <Spinner className="h-4 w-4" /> : <Sparkles className="h-4 w-4" />}
            {createJob.isPending ? "Extracting..." : "Add job"}
          </Button>
        </form>
      </Card>
    </div>
  );
}
