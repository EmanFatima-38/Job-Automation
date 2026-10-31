import { RequireAuth } from "@/components/auth/RequireAuth";
import { Sidebar } from "@/components/dashboard/Sidebar";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <RequireAuth>
      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-1 overflow-y-auto p-8">
          <div className="mx-auto max-w-6xl animate-fade-in">{children}</div>
        </main>
      </div>
    </RequireAuth>
  );
}
