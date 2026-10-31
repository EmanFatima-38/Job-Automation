import { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "rounded-xl border border-zinc-200/80 bg-white p-6 shadow-sm shadow-zinc-900/[0.03] dark:border-zinc-800 dark:bg-zinc-900 dark:shadow-none",
        className
      )}
      {...props}
    />
  );
}

export function CardHover({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <Card
      className={cn(
        "transition-all duration-150 hover:-translate-y-0.5 hover:shadow-md hover:shadow-zinc-900/[0.06] hover:border-zinc-300 dark:hover:border-zinc-700",
        className
      )}
      {...props}
    />
  );
}
