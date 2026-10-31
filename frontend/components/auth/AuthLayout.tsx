import { Rocket } from "lucide-react";

export function AuthLayout({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: React.ReactNode;
}) {
  return (
    <div className="relative flex flex-1 items-center justify-center overflow-hidden p-6">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10"
        style={{
          background:
            "radial-gradient(ellipse 80% 50% at 50% -10%, rgba(99,102,241,0.12), transparent)",
        }}
      />
      <div className="w-full max-w-sm animate-fade-in">
        <div className="mb-8 flex flex-col items-center text-center">
          <div className="brand-gradient mb-4 flex h-12 w-12 items-center justify-center rounded-2xl shadow-lg shadow-indigo-500/25">
            <Rocket className="h-6 w-6 text-white" strokeWidth={2.25} />
          </div>
          <h1 className="text-xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
            {title}
          </h1>
          <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">{subtitle}</p>
        </div>
        {children}
      </div>
    </div>
  );
}
