"use client";

import {
  LayoutDashboard,
  FileText,
  Briefcase,
  ClipboardList,
  Settings,
  LogOut,
  Rocket,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { cn } from "@/lib/utils";
import { useAuth } from "@/providers/AuthProvider";

const links = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/jobs/new", label: "Add Job", icon: Briefcase },
  { href: "/resume", label: "Resume", icon: FileText },
  { href: "/applications", label: "Applications", icon: ClipboardList },
  { href: "/settings", label: "Settings", icon: Settings },
];

function initialsFor(email: string | undefined): string {
  if (!email) return "?";
  return email[0]?.toUpperCase() ?? "?";
}

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const router = useRouter();

  function handleLogout() {
    logout();
    router.push("/login");
  }

  return (
    <aside className="flex w-60 flex-col border-r border-zinc-200/80 bg-white dark:border-zinc-800 dark:bg-zinc-900">
      <div className="flex items-center gap-2.5 px-5 py-5">
        <div className="brand-gradient flex h-8 w-8 shrink-0 items-center justify-center rounded-lg shadow-sm shadow-indigo-500/30">
          <Rocket className="h-[18px] w-[18px] text-white" strokeWidth={2.25} />
        </div>
        <span className="text-[17px] font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
          ApplyPilot
        </span>
      </div>

      <nav className="flex-1 space-y-0.5 px-3">
        {links.map(({ href, label, icon: Icon }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "group relative flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-brand/[0.08] text-brand-dark dark:bg-brand/[0.15] dark:text-brand-light"
                  : "text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-zinc-50"
              )}
            >
              {active && (
                <span className="brand-gradient absolute left-0 top-1/2 h-5 w-1 -translate-y-1/2 rounded-r-full" />
              )}
              <Icon
                className={cn(
                  "h-4 w-4 shrink-0",
                  active ? "text-brand-dark dark:text-brand-light" : "text-zinc-400 group-hover:text-zinc-600 dark:group-hover:text-zinc-300"
                )}
              />
              {label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-zinc-200/80 p-3 dark:border-zinc-800">
        <div className="flex items-center gap-2.5 rounded-lg px-2 py-2">
          <div className="brand-gradient flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-semibold text-white">
            {initialsFor(user?.email)}
          </div>
          <p className="truncate text-xs font-medium text-zinc-600 dark:text-zinc-400">
            {user?.email}
          </p>
        </div>
        <button
          onClick={handleLogout}
          className="mt-1 flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium text-zinc-500 transition-colors hover:bg-zinc-100 hover:text-zinc-900 dark:text-zinc-500 dark:hover:bg-zinc-800 dark:hover:text-zinc-50"
        >
          <LogOut className="h-4 w-4" />
          Log out
        </button>
      </div>
    </aside>
  );
}
