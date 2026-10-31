"use client";

import { Mail, MapPin, RadioTower, Save, Search, Send } from "lucide-react";
import { useState } from "react";
import { DiscoveryPreferences } from "@/components/dashboard/DiscoveryPreferences";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { PageSpinner, Spinner } from "@/components/ui/spinner";
import { useTriggerCrawl } from "@/hooks/useCrawl";
import { useEmailAccount, useSaveEmailAccount, useTestEmailAccount } from "@/hooks/useEmailAccount";
import { useProfile, useUpdateProfile } from "@/hooks/useProfile";
import { ApiError } from "@/lib/api-client";
import type { CrawlRun, Profile, EmailAccount } from "@/lib/types";

export default function SettingsPage() {
  const { data: profile, isLoading } = useProfile();
  const { data: emailAccount, isLoading: emailLoading } = useEmailAccount();
  if (isLoading || emailLoading) return <PageSpinner />;
  if (!profile) return <p role="alert">Could not load your profile. Please refresh.</p>;
  return <SettingsForm key={JSON.stringify([profile, emailAccount])} profile={profile} emailAccount={emailAccount ?? null} />;
}

function SettingsForm({ profile, emailAccount }: { profile: Profile; emailAccount: EmailAccount | null }) {
  const updateProfile = useUpdateProfile();
  const triggerCrawl = useTriggerCrawl();
  const saveEmailAccount = useSaveEmailAccount();
  const testEmailAccount = useTestEmailAccount();

  const [country, setCountry] = useState(profile.country ?? "");
  const [city, setCity] = useState(profile.city ?? "");
  const [keywords, setKeywords] = useState(profile.search_keywords ?? "");
  const [crawlEnabled, setCrawlEnabled] = useState(profile.crawl_enabled);
  const [lastRun, setLastRun] = useState<CrawlRun | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [followupEnabled, setFollowupEnabled] = useState(profile.followup_enabled);
  const [followupFirstDays, setFollowupFirstDays] = useState(profile.followup_first_days);
  const [followupIntervalDays, setFollowupIntervalDays] = useState(profile.followup_interval_days);
  const [followupMaxCount, setFollowupMaxCount] = useState(profile.followup_max_count);
  const [followupError, setFollowupError] = useState<string | null>(null);

  const [smtpHost, setSmtpHost] = useState(emailAccount?.smtp_host ?? "");
  const [smtpPort, setSmtpPort] = useState(emailAccount?.smtp_port ?? 587);
  const [smtpUsername, setSmtpUsername] = useState(emailAccount?.smtp_username ?? "");
  const [smtpPassword, setSmtpPassword] = useState("");
  const [fromName, setFromName] = useState(emailAccount?.from_name ?? "");
  const [fromEmail, setFromEmail] = useState(emailAccount?.from_email ?? "");
  const [useTls, setUseTls] = useState(emailAccount?.use_tls ?? true);
  const [emailError, setEmailError] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<{ ok: boolean; error: string | null } | null>(null);

  async function handleSaveFollowupSettings(e: React.FormEvent) {
    e.preventDefault();
    setFollowupError(null);
    try {
      await updateProfile.mutateAsync({
        followup_enabled: followupEnabled,
        followup_first_days: followupFirstDays,
        followup_interval_days: followupIntervalDays,
        followup_max_count: followupMaxCount,
      });
    } catch (err) {
      setFollowupError(err instanceof ApiError ? err.message : "Could not save follow-up settings");
    }
  }

  async function handleSaveEmailAccount(e: React.FormEvent) {
    e.preventDefault();
    setEmailError(null);
    setTestResult(null);
    try {
      await saveEmailAccount.mutateAsync({
        smtp_host: smtpHost,
        smtp_port: smtpPort,
        smtp_username: smtpUsername,
        smtp_password: smtpPassword,
        from_name: fromName || null,
        from_email: fromEmail,
        use_tls: useTls,
      });
      setSmtpPassword("");
    } catch (err) {
      setEmailError(err instanceof ApiError ? err.message : "Could not save email account");
    }
  }

  async function handleTestEmailAccount() {
    setEmailError(null);
    try {
      const result = await testEmailAccount.mutateAsync();
      setTestResult(result);
    } catch (err) {
      setEmailError(err instanceof ApiError ? err.message : "Could not send test email");
    }
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await updateProfile.mutateAsync({
        country: country || null,
        city: city || null,
        search_keywords: keywords || null,
        crawl_enabled: crawlEnabled,
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save settings");
    }
  }

  async function handleRunNow() {
    setError(null);
    try {
      const run = await triggerCrawl.mutateAsync();
      setLastRun(run);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Crawl failed to run");
    }
  }


  return (
    <div className="max-w-xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
          Settings
        </h1>
        <p className="mt-0.5 text-sm text-zinc-500 dark:text-zinc-400">
          Tell ApplyPilot where and what to search for.
        </p>
      </div>

      <Card>
        <h2 className="mb-4 flex items-center gap-2 font-medium text-zinc-900 dark:text-zinc-50">
          <RadioTower className="h-4 w-4 text-zinc-400" />
          Job search &amp; auto-crawl
        </h2>
        <DiscoveryPreferences />
        <form onSubmit={handleSave} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <Field label="Country">
              <Input
                value={country}
                onChange={(e) => setCountry(e.target.value)}
                placeholder="e.g. Pakistan"
              />
            </Field>
            <Field label="City">
              <Input
                value={city}
                onChange={(e) => setCity(e.target.value)}
                placeholder="e.g. Lahore"
              />
            </Field>
          </div>
          <Field label="Search keywords">
            <Input
              value={keywords}
              onChange={(e) => setKeywords(e.target.value)}
              placeholder="e.g. AI Engineer, Backend Developer, Full Stack Developer"
            />
          </Field>
          <p className="-mt-2 text-xs text-zinc-400 dark:text-zinc-500">
            Country, city, and search keywords are auto-filled from your primary resume
            (including related roles it suggests, like backend/full-stack/frontend for an AI
            engineer) - edit anytime, your changes stick.
          </p>
          <label className="flex items-center gap-2 text-sm text-zinc-700 dark:text-zinc-300">
            <input
              type="checkbox"
              checked={crawlEnabled}
              onChange={(e) => setCrawlEnabled(e.target.checked)}
              className="h-4 w-4 rounded border-zinc-300 text-brand focus:ring-brand/30 dark:border-zinc-700"
            />
            Automatically search for jobs every hour
          </label>

          {error && (
            <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600 dark:bg-red-950/40 dark:text-red-400">
              {error}
            </p>
          )}

          <div className="flex gap-2">
            <Button type="submit" disabled={updateProfile.isPending}>
              {updateProfile.isPending ? <Spinner className="h-4 w-4" /> : <Save className="h-4 w-4" />}
              {updateProfile.isPending ? "Saving..." : "Save"}
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={handleRunNow}
              disabled={triggerCrawl.isPending || !profile?.crawl_enabled}
            >
              {triggerCrawl.isPending ? <Spinner className="h-3.5 w-3.5" /> : <Search className="h-3.5 w-3.5" />}
              {triggerCrawl.isPending ? "Running..." : "Run crawl now"}
            </Button>
          </div>
          {!profile?.crawl_enabled && (
            <p className="flex items-center gap-1.5 text-xs text-zinc-500 dark:text-zinc-500">
              <MapPin className="h-3 w-3" />
              Enable and save auto-crawl above before running it manually.
            </p>
          )}
        </form>
      </Card>

      <Card>
        <h2 className="mb-4 flex items-center gap-2 font-medium text-zinc-900 dark:text-zinc-50">
          <Mail className="h-4 w-4 text-zinc-400" />
          Email &amp; follow-ups
        </h2>

        <form onSubmit={handleSaveEmailAccount} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <Field label="SMTP host">
              <Input
                value={smtpHost}
                onChange={(e) => setSmtpHost(e.target.value)}
                placeholder="e.g. smtp.gmail.com"
                required
              />
            </Field>
            <Field label="SMTP port">
              <Input
                type="number"
                value={smtpPort}
                onChange={(e) => setSmtpPort(Number(e.target.value))}
                required
              />
            </Field>
          </div>
          <Field label="SMTP username">
            <Input
              value={smtpUsername}
              onChange={(e) => setSmtpUsername(e.target.value)}
              required
            />
          </Field>
          <Field label={emailAccount ? "SMTP password (re-enter to update)" : "SMTP password"}>
            <Input
              type="password"
              value={smtpPassword}
              onChange={(e) => setSmtpPassword(e.target.value)}
              placeholder={emailAccount ? "Leave blank only if not changing other fields" : ""}
              required
            />
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="From name (optional)">
              <Input value={fromName} onChange={(e) => setFromName(e.target.value)} />
            </Field>
            <Field label="From email">
              <Input
                type="email"
                value={fromEmail}
                onChange={(e) => setFromEmail(e.target.value)}
                required
              />
            </Field>
          </div>
          <label className="flex items-center gap-2 text-sm text-zinc-700 dark:text-zinc-300">
            <input
              type="checkbox"
              checked={useTls}
              onChange={(e) => setUseTls(e.target.checked)}
              className="h-4 w-4 rounded border-zinc-300 text-brand focus:ring-brand/30 dark:border-zinc-700"
            />
            Use STARTTLS
          </label>

          {emailError && (
            <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600 dark:bg-red-950/40 dark:text-red-400">
              {emailError}
            </p>
          )}

          <div className="flex items-center gap-2">
            <Button type="submit" disabled={saveEmailAccount.isPending}>
              {saveEmailAccount.isPending ? <Spinner className="h-4 w-4" /> : <Save className="h-4 w-4" />}
              {saveEmailAccount.isPending ? "Saving..." : "Save account"}
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={handleTestEmailAccount}
              disabled={testEmailAccount.isPending || !emailAccount}
            >
              {testEmailAccount.isPending ? <Spinner className="h-3.5 w-3.5" /> : <Send className="h-3.5 w-3.5" />}
              {testEmailAccount.isPending ? "Sending..." : "Send test email"}
            </Button>
            {testResult && (
              <Badge status={testResult.ok ? "extracted" : "failed"}>
                {testResult.ok ? "Test sent" : testResult.error ?? "Test failed"}
              </Badge>
            )}
          </div>
          {!emailAccount && (
            <p className="text-xs text-zinc-500 dark:text-zinc-500">
              Save an account above before you can send a test email.
            </p>
          )}
        </form>

        <hr className="my-5 border-zinc-200 dark:border-zinc-800" />

        <form onSubmit={handleSaveFollowupSettings} className="space-y-4">
          <label className="flex items-center gap-2 text-sm text-zinc-700 dark:text-zinc-300">
            <input
              type="checkbox"
              checked={followupEnabled}
              onChange={(e) => setFollowupEnabled(e.target.checked)}
              className="h-4 w-4 rounded border-zinc-300 text-brand focus:ring-brand/30 dark:border-zinc-700"
            />
            Automatically send follow-up emails on applications gone quiet
          </label>

          <div className="grid grid-cols-3 gap-3">
            <Field label="First follow-up after (days)">
              <Input
                type="number"
                min={0}
                value={followupFirstDays}
                onChange={(e) => setFollowupFirstDays(Number(e.target.value))}
              />
            </Field>
            <Field label="Days between follow-ups">
              <Input
                type="number"
                min={0}
                value={followupIntervalDays}
                onChange={(e) => setFollowupIntervalDays(Number(e.target.value))}
              />
            </Field>
            <Field label="Max follow-ups per application">
              <Input
                type="number"
                min={0}
                value={followupMaxCount}
                onChange={(e) => setFollowupMaxCount(Number(e.target.value))}
              />
            </Field>
          </div>

          <p className="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:bg-amber-950/30 dark:text-amber-300">
            Follow-ups send automatically with no review step. Only applications where a
            contact email was found on the posting are eligible - many crawled postings won&apos;t
            have one. ApplyPilot cannot detect if the recruiter already replied, so the
            max-follow-ups cap above is the only real safeguard against over-following-up.
          </p>

          {followupError && (
            <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600 dark:bg-red-950/40 dark:text-red-400">
              {followupError}
            </p>
          )}

          <Button type="submit" disabled={updateProfile.isPending}>
            {updateProfile.isPending ? <Spinner className="h-4 w-4" /> : <Save className="h-4 w-4" />}
            {updateProfile.isPending ? "Saving..." : "Save follow-up settings"}
          </Button>
        </form>
      </Card>

      {lastRun && (
        <Card>
          <div className="mb-2 flex items-center gap-2">
            <h2 className="font-medium text-zinc-900 dark:text-zinc-50">Last run</h2>
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
          </div>
          <p className="text-sm text-zinc-600 dark:text-zinc-400">
            Found {lastRun.jobs_found} jobs, added {lastRun.jobs_created} new.
          </p>
          <ul className="mt-2 space-y-1.5 text-sm">
            {lastRun.source_results.map((r, i) => (
              <li key={i} className="flex items-center gap-2">
                <span className="font-medium capitalize text-zinc-700 dark:text-zinc-300">
                  {r.source}
                </span>
                {r.tier && <span className="text-zinc-500">({r.tier})</span>}
                {r.error ? (
                  <span className="text-red-600 dark:text-red-400">{r.error}</span>
                ) : (
                  <span className="text-emerald-600 dark:text-emerald-400">{r.jobs_found} found</span>
                )}
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}
