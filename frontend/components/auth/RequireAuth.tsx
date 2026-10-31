"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { PageSpinner } from "@/components/ui/spinner";
import { useAuth } from "@/providers/AuthProvider";

export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/login");
    }
  }, [loading, user, router]);

  if (loading || !user) {
    return <PageSpinner />;
  }

  return <>{children}</>;
}
