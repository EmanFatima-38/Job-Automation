import { ButtonHTMLAttributes, forwardRef } from "react";

import { cn } from "@/lib/utils";

type Variant = "primary" | "secondary" | "ghost" | "danger";

const variantClasses: Record<Variant, string> = {
  primary:
    "brand-gradient text-white shadow-sm shadow-indigo-500/20 hover:brightness-110 hover:shadow-md hover:shadow-indigo-500/30 active:brightness-95",
  secondary:
    "bg-white text-zinc-700 border border-zinc-200 shadow-sm hover:border-zinc-300 hover:bg-zinc-50 dark:bg-zinc-800 dark:text-zinc-200 dark:border-zinc-700 dark:hover:bg-zinc-750 dark:hover:border-zinc-600",
  ghost:
    "bg-transparent text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-zinc-50",
  danger:
    "bg-white text-red-600 border border-red-200 shadow-sm hover:bg-red-50 hover:border-red-300 dark:bg-zinc-900 dark:border-red-900/50 dark:hover:bg-red-950/40",
};

export const Button = forwardRef<
  HTMLButtonElement,
  ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }
>(({ className, variant = "primary", disabled, ...props }, ref) => (
  <button
    ref={ref}
    disabled={disabled}
    className={cn(
      "inline-flex items-center justify-center gap-1.5 rounded-lg px-4 py-2 text-sm font-medium transition-all duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:opacity-50 disabled:pointer-events-none disabled:shadow-none",
      variantClasses[variant],
      className
    )}
    {...props}
  />
));
Button.displayName = "Button";
