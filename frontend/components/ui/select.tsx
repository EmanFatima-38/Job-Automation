import { SelectHTMLAttributes, forwardRef } from "react";

import { cn } from "@/lib/utils";

export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(
  ({ className, ...props }, ref) => (
    <select
      ref={ref}
      className={cn(
        "rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-700 shadow-sm transition-colors focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/20 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-200",
        className
      )}
      {...props}
    />
  )
);
Select.displayName = "Select";
