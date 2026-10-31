"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useProfile } from "@/hooks/useProfile";
import { useResumes } from "@/hooks/useResumes";
import type { CandidateProject, DiscoveryPreferenceValues as Preferences } from "@/lib/types";



export function DiscoveryPreferences() {
  const { data } = useProfile();
  if (!data) return null;
  return <PreferencesForm key={JSON.stringify(data.preferences)} initial={data.preferences ?? {}} />;
}

function PreferencesForm({ initial }: { initial: Preferences }) {
  const [prefs, setPrefs] = useState<Preferences>(initial);
  const [projects, setProjects] = useState<CandidateProject[]>(initial.projects ?? []);
  const [error, setError] = useState("");
  const client = useQueryClient();
  const { data: resumes } = useResumes();
  const primary = resumes?.find((r) => r.is_primary)?.structured_profile;
  const { data: deliveries = [] } = useQuery({queryKey: ["opportunityDeliveries"], queryFn: () => apiFetch<{job_id: string; status: string; created_at: string; error: string | null}[]>("/notifications/history")});
  const save = useMutation({ mutationFn: (preferences: Preferences) => apiFetch("/profile", { method: "PATCH", body: JSON.stringify({ preferences }) }),
    onSuccess: () => client.invalidateQueries({ queryKey: ["profile"] }) });
  const portfolio = useMutation({ mutationFn: () => apiFetch<Record<string, {error?: string; refreshed_at?: string}>>("/profile/portfolio/refresh", { method: "POST" }),
    onSuccess: () => client.invalidateQueries({ queryKey: ["profile"] }) });
  const csvFields: [keyof Preferences, string][] = [["roles", "Preferred roles"], ["skills", "Skills and frameworks"], ["employment_types", "Employment types: internship, full_time, part_time, contract"], ["seniority", "Seniority: intern, entry level, junior"], ["cities", "Preferred cities"], ["countries", "Preferred countries"], ["excluded_companies", "Excluded companies"], ["excluded_keywords", "Excluded keywords"], ["portfolio_urls", "Portfolio URLs (up to five)"]];
  const inputClass = "mt-1 w-full rounded-md border border-zinc-300 bg-transparent p-2 text-sm dark:border-zinc-700";
  return <Card className="mb-6 space-y-4">
    <h2 className="font-semibold">Discovery preferences</h2>
    <p className="text-sm text-zinc-500">Review your CV suggestions and save the preferences used for searches and opportunity emails. Comma-separate list fields.</p>
    {primary && <details className="text-sm"><summary className="cursor-pointer">Review primary CV suggestions</summary><div className="my-3 space-y-2"><p>{primary.summary}</p><p>Suggested roles: {primary.target_roles?.join(", ") || "None extracted"}</p><p>Skills: {primary.skills.join(", ")}</p>{primary.projects?.map((p, i) => <p key={i}>{p.name}: {p.description}</p>)}</div><Button type="button" variant="secondary" onClick={() => { setPrefs({ ...prefs, roles: prefs.roles?.length ? prefs.roles : primary.target_roles ?? [], skills: prefs.skills?.length ? prefs.skills : primary.skills, portfolio_urls: prefs.portfolio_urls?.length ? prefs.portfolio_urls : primary.portfolio_urls ?? [], github_url: prefs.github_url || primary.github_url || "" }); if (!projects.length) setProjects(primary.projects ?? []); }}>Use suggestions for empty fields</Button></details>}
    <form className="space-y-4" onSubmit={async (event) => { event.preventDefault(); setError(""); try { await save.mutateAsync({ ...prefs, projects }); } catch (e) { setError(e instanceof Error ? e.message : "Could not save preferences"); } }}>
      <div className="grid gap-3 sm:grid-cols-2">{csvFields.map(([key, label]) => <label key={key} className="text-sm">{label}<input className={inputClass} defaultValue={(prefs[key] as string[] | undefined)?.join(", ") ?? ""} key={`${key}-${JSON.stringify(initial)}-${key === 'roles' || key === 'skills' ? JSON.stringify(prefs[key]) : ''}`} onBlur={(e) => setPrefs({ ...prefs, [key]: e.target.value.split(",").map((v) => v.trim()).filter(Boolean) })} /></label>)}</div>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="text-sm">GitHub profile URL<input className={inputClass} value={prefs.github_url ?? ""} onChange={(e) => setPrefs({ ...prefs, github_url: e.target.value })} /></label>
        <label className="text-sm">Applicant country for remote work<input className={inputClass} value={prefs.remote_country ?? ""} onChange={(e) => setPrefs({ ...prefs, remote_country: e.target.value })} /></label>
      </div>
      <label className="block text-sm"><input type="checkbox" checked={prefs.remote ?? false} onChange={(e) => setPrefs({ ...prefs, remote: e.target.checked })} /> Include remote opportunities</label>
      <div className="space-y-3"><h3 className="text-sm font-medium">Projects</h3>{projects.map((project, index) => <div key={index} className="rounded-lg border p-3 space-y-2">
        <input aria-label={`Project ${index + 1} name`} placeholder="Project name" className={inputClass} value={project.name ?? ""} onChange={(e) => setProjects(projects.map((p, i) => i === index ? { ...p, name: e.target.value } : p))} />
        <textarea aria-label={`Project ${index + 1} description`} placeholder="What you built and your contribution" className={inputClass} value={project.description ?? ""} onChange={(e) => setProjects(projects.map((p, i) => i === index ? { ...p, description: e.target.value } : p))} />
        <input aria-label={`Project ${index + 1} technologies`} placeholder="Technologies, separated by commas" className={inputClass} defaultValue={project.technologies?.join(", ") ?? ""} onBlur={(e) => setProjects(projects.map((p, i) => i === index ? { ...p, technologies: e.target.value.split(",").map((v) => v.trim()).filter(Boolean) } : p))} />
        <Button variant="secondary" type="button" onClick={() => setProjects(projects.filter((_, i) => i !== index))}>Remove project</Button>
      </div>)}<Button type="button" variant="secondary" onClick={() => setProjects([...projects, { name: "", description: "", technologies: [] }])}>Add project</Button></div>
      <div className="grid gap-3 sm:grid-cols-3">
        <label className="text-sm">Maximum posting age (days)<input className={inputClass} type="number" min={1} max={365} value={prefs.max_age_days ?? ""} onChange={(e) => setPrefs({ ...prefs, max_age_days: e.target.value ? Number(e.target.value) : null })} /></label>
        <label className="text-sm">Queries per search<input className={inputClass} type="number" min={1} max={12} value={prefs.max_queries ?? 6} onChange={(e) => setPrefs({ ...prefs, max_queries: Number(e.target.value) })} /></label>
        <label className="text-sm">Results per source<input className={inputClass} type="number" min={1} max={30} value={prefs.results_per_source ?? 10} onChange={(e) => setPrefs({ ...prefs, results_per_source: Number(e.target.value) })} /></label>
      </div>
      <label className="block text-sm">Search depth<select className={inputClass} value={prefs.search_depth ?? "basic"} onChange={(e) => setPrefs({ ...prefs, search_depth: e.target.value })}><option value="basic">Basic</option><option value="advanced">Advanced (more API usage)</option></select></label>
      <div className="space-y-3 rounded-lg border border-zinc-200 p-3 dark:border-zinc-700">
        <label className="text-sm"><input type="checkbox" checked={prefs.notifications_enabled ?? false} onChange={(e) => setPrefs({ ...prefs, notifications_enabled: e.target.checked })} /> Email me new matching opportunities using my connected SMTP account</label>
        <p className="text-xs text-zinc-500">Delivered to your account email. Uses the preferences above and requires a verified active vacancy with no unresolved eligibility concerns. Employer follow-ups have separate controls.</p>
        <div className="grid gap-3 sm:grid-cols-2"><label className="text-sm">Minimum estimated fit<input type="number" min={0} max={100} className={inputClass} value={prefs.notification_min_score ?? 75} onChange={(e) => setPrefs({ ...prefs, notification_min_score: Number(e.target.value) })} /></label><label className="text-sm">Minimum hours between digests<input type="number" min={1} max={168} className={inputClass} value={prefs.notification_hours ?? 24} onChange={(e) => setPrefs({ ...prefs, notification_hours: Number(e.target.value) })} /></label></div>
      </div>
      <Button disabled={save.isPending} type="submit">{save.isPending ? "Saving…" : "Save discovery preferences"}</Button>
    </form>
    {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
    <Button type="button" variant="secondary" disabled={portfolio.isPending} onClick={() => portfolio.mutate()}>{portfolio.isPending ? "Reading portfolio…" : "Refresh saved portfolio URLs"}</Button>
    <p className="text-xs text-zinc-500">Save URL changes first. Cached pages refresh at most once per day.</p>
    {portfolio.error && <p className="text-sm text-red-600">{portfolio.error.message}</p>}
    {portfolio.data && Object.entries(portfolio.data).map(([url, result]) => <p key={url} className="break-all text-xs">{url}: {result.error || `Read ${result.refreshed_at}`}</p>)}
    {!!deliveries.length && <details><summary className="cursor-pointer text-sm">Opportunity email history</summary>{deliveries.map((d) => <p className="text-xs" key={`${d.job_id}-${d.created_at}`}>{new Date(d.created_at).toLocaleString()} · {d.status} {d.error && `· ${d.error}`}</p>)}</details>}
  </Card>;
}

