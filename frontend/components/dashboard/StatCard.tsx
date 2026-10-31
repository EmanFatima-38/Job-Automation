import { type LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";

const colorMap = {
  zinc: "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400",
  blue: "bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400",
  amber: "bg-amber-50 text-amber-600 dark:bg-amber-900/30 dark:text-amber-400",
  emerald: "bg-emerald-50 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400",
  red: "bg-red-50 text-red-600 dark:bg-red-900/30 dark:text-red-400",
} as const;

export function StatCard({
  label,
  value,
  icon: Icon,
  color,
}: {
  label: string;
  value: number | undefined;
  icon: LucideIcon;
  color: keyof typeof colorMap;
}) {
  return (
    <div className="rounded-xl border border-zinc-200/80 bg-white p-4 shadow-sm shadow-zinc-900/[0.03] dark:border-zinc-800 dark:bg-zinc-900 dark:shadow-none">
      <div className={cn("mb-3 inline-flex h-9 w-9 items-center justify-center rounded-lg", colorMap[color])}>
        <Icon className="h-[18px] w-[18px]" strokeWidth={2.25} />
      </div>
      <p className="text-2xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
        {value ?? "–"}
      </p>
      <p className="text-sm text-zinc-500 dark:text-zinc-400">{label}</p>
    </div>
  );
}
