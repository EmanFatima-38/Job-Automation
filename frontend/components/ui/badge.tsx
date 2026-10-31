import { HTMLAttributes } from "react";
import {
  CheckCircle2,
  Circle,
  Clock,
  type LucideIcon,
  Send,
  Star,
  Trophy,
  X,
  XCircle,
} from "lucide-react";

import { cn } from "@/lib/utils";

const statusClasses: Record<string, string> = {
  pending: "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300",
  parsing: "bg-amber-50 text-amber-700 ring-1 ring-inset ring-amber-600/20 dark:bg-amber-900/30 dark:text-amber-300 dark:ring-amber-400/20",
  extracting: "bg-amber-50 text-amber-700 ring-1 ring-inset ring-amber-600/20 dark:bg-amber-900/30 dark:text-amber-300 dark:ring-amber-400/20",
  parsed: "bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-600/20 dark:bg-emerald-900/30 dark:text-emerald-300 dark:ring-emerald-400/20",
  extracted: "bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-600/20 dark:bg-emerald-900/30 dark:text-emerald-300 dark:ring-emerald-400/20",
  failed: "bg-red-50 text-red-700 ring-1 ring-inset ring-red-600/20 dark:bg-red-900/30 dark:text-red-300 dark:ring-red-400/20",
  saved: "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300",
  applied: "bg-blue-50 text-blue-700 ring-1 ring-inset ring-blue-600/20 dark:bg-blue-900/30 dark:text-blue-300 dark:ring-blue-400/20",
  interview: "bg-amber-50 text-amber-700 ring-1 ring-inset ring-amber-600/20 dark:bg-amber-900/30 dark:text-amber-300 dark:ring-amber-400/20",
  offer: "bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-600/20 dark:bg-emerald-900/30 dark:text-emerald-300 dark:ring-emerald-400/20",
  rejected: "bg-red-50 text-red-700 ring-1 ring-inset ring-red-600/20 dark:bg-red-900/30 dark:text-red-300 dark:ring-red-400/20",
};

const statusIcons: Record<string, LucideIcon> = {
  pending: Circle,
  parsing: Clock,
  extracting: Clock,
  parsed: CheckCircle2,
  extracted: CheckCircle2,
  failed: XCircle,
  saved: Circle,
  applied: Send,
  interview: Star,
  offer: Trophy,
  rejected: X,
};

export function Badge({
  status,
  icon = true,
  className,
  children,
  ...props
}: HTMLAttributes<HTMLSpanElement> & { status?: string; icon?: boolean }) {
  const Icon = status ? statusIcons[status] : undefined;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium capitalize",
        status ? statusClasses[status] ?? statusClasses.pending : statusClasses.pending,
        className
      )}
      {...props}
    >
      {icon && Icon && <Icon className="h-3 w-3" strokeWidth={2.5} />}
      {children}
    </span>
  );
}
