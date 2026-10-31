import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client";
import type { Profile } from "@/lib/types";

export function useProfile() {
  return useQuery({
    queryKey: ["profile"],
    queryFn: () => apiFetch<Profile>("/profile"),
  });
}

export function useUpdateProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<Profile>) =>
      apiFetch<Profile>("/profile", { method: "PATCH", body: JSON.stringify(data) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["profile"] }),
  });
}
