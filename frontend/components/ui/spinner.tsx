import { Loader2 } from "lucide-react";

import { cn } from "@/lib/utils";

export function Spinner({ className }: { className?: string }) {
  return <Loader2 className={cn("h-4 w-4 animate-spin", className)} />;
}

export function PageSpinner() {
  return (
    <div className="flex flex-1 items-center justify-center py-20">
      <Spinner className="h-6 w-6 text-brand" />
    </div>
  );
}
