"use client";

import { FileText, RotateCw, Star, Trash2, Upload } from "lucide-react";
import { useRef, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Spinner } from "@/components/ui/spinner";
import {
  useDeleteResume,
  useReparseResume,
  useResumes,
  useSetPrimaryResume,
  useUploadResume,
} from "@/hooks/useResumes";
import { ApiError } from "@/lib/api-client";

export default function ResumePage() {
  const { data: resumes, isLoading } = useResumes();
  const upload = useUploadResume();
  const setPrimary = useSetPrimaryResume();
  const reparse = useReparseResume();
  const deleteResume = useDeleteResume();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setError(null);
    try {
      await upload.mutateAsync(file);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed");
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  const fileInput = (
    <input
      ref={fileInputRef}
      type="file"
      accept=".pdf,.docx"
      className="hidden"
      onChange={handleFileChange}
    />
  );

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
            Resume
          </h1>
          <p className="mt-0.5 text-sm text-zinc-500 dark:text-zinc-400">
            Upload the resume ApplyPilot should match against.
          </p>
        </div>
        {!!resumes?.length && (
          <Button onClick={() => fileInputRef.current?.click()} disabled={upload.isPending}>
            {upload.isPending ? <Spinner className="h-4 w-4" /> : <Upload className="h-4 w-4" />}
            {upload.isPending ? "Uploading..." : "Upload resume"}
          </Button>
        )}
        {fileInput}
      </div>

      {error && (
        <p className="mb-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600 dark:bg-red-950/40 dark:text-red-400">
          {error}
        </p>
      )}

      {isLoading && (
        <Card className="space-y-3">
          <Skeleton className="h-5 w-1/3" />
          <Skeleton className="h-4 w-2/3" />
          <Skeleton className="h-4 w-1/2" />
        </Card>
      )}

      {!isLoading && resumes?.length === 0 && (
        <button
          onClick={() => fileInputRef.current?.click()}
          className="flex w-full flex-col items-center gap-3 rounded-xl border-2 border-dashed border-zinc-300 p-12 text-center transition-colors hover:border-brand hover:bg-brand/[0.03] dark:border-zinc-700 dark:hover:border-brand"
        >
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-zinc-100 dark:bg-zinc-800">
            <Upload className="h-5 w-5 text-zinc-400" />
          </div>
          <div>
            <p className="font-medium text-zinc-700 dark:text-zinc-300">
              Upload a PDF or DOCX to get started
            </p>
            <p className="mt-0.5 text-sm text-zinc-500 dark:text-zinc-400">
              Click to browse your files
            </p>
          </div>
        </button>
      )}

      <div className="space-y-4">
        {resumes?.map((resume) => (
          <Card key={resume.id}>
            <div className="flex items-start justify-between gap-4">
              <div className="flex min-w-0 gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-zinc-100 text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400">
                  <FileText className="h-[18px] w-[18px]" />
                </div>
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="truncate font-medium text-zinc-900 dark:text-zinc-50">
                      {resume.original_filename}
                    </h3>
                    {resume.is_primary && (
                      <Badge status="extracted" icon={false}>
                        <Star className="h-3 w-3" fill="currentColor" /> Primary
                      </Badge>
                    )}
                    <Badge status={resume.parse_status}>{resume.parse_status}</Badge>
                  </div>
                  {resume.parse_error && (
                    <p className="mt-1.5 text-xs text-red-600 dark:text-red-400">
                      {resume.parse_error}
                    </p>
                  )}
                  {resume.structured_profile && (
                    <div className="mt-2 space-y-2">
                      <p className="text-sm text-zinc-600 dark:text-zinc-400">
                        {resume.structured_profile.summary}
                      </p>
                      <div className="flex flex-wrap gap-1.5">
                        {resume.structured_profile.skills.map((skill) => (
                          <span
                            key={skill}
                            className="rounded-full bg-zinc-100 px-2 py-0.5 text-xs text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300"
                          >
                            {skill}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
              <div className="flex shrink-0 gap-2">
                {resume.parse_status === "failed" && (
                  <Button
                    variant="secondary"
                    onClick={() => reparse.mutate(resume.id)}
                    disabled={reparse.isPending}
                  >
                    <RotateCw className="h-3.5 w-3.5" />
                    Retry
                  </Button>
                )}
                {!resume.is_primary && (
                  <Button variant="secondary" onClick={() => setPrimary.mutate(resume.id)}>
                    Set primary
                  </Button>
                )}
                <Button
                  variant="ghost"
                  onClick={() => deleteResume.mutate(resume.id)}
                  className="text-zinc-400 hover:text-red-600 dark:hover:text-red-400"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
