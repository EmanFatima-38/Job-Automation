import { cn } from "@/lib/utils";

export function MatchPill({ score }: { score: number | null | undefined }) {
  if (score == null) {
    return <span className="text-sm text-zinc-400">—</span>;
  }

  const tier =
    score >= 70 ? "emerald" : score >= 40 ? "amber" : "red";

  const colors = {
    emerald: "bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300",
    amber: "bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300",
    red: "bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300",
  } as const;

  const bar = {
    emerald: "bg-emerald-500",
    amber: "bg-amber-500",
    red: "bg-red-500",
  } as const;

  return (
    <div className="flex items-center gap-2" title="Estimated fit, not a hiring probability">
      <span
        className={cn(
          "inline-flex min-w-[3rem] items-center justify-center rounded-md px-1.5 py-0.5 text-xs font-semibold",
          colors[tier]
        )}
      >
        {score}/100
      </span>
      <div className="h-1.5 w-12 overflow-hidden rounded-full bg-zinc-100 dark:bg-zinc-800">
        <div
          className={cn("h-full rounded-full transition-all", bar[tier])}
          style={{ width: `${Math.min(100, Math.max(0, score))}%` }}
        />
      </div>
    </div>
  );
}
