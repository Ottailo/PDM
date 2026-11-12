import { QueryCache, QueryClient, useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { ApiError, clearReplayContext, get, setReplayContext } from "./api";
import type { Identity } from "./types";
export const queryClient = new QueryClient({
  queryCache: new QueryCache({
    onError: (error, query) => {
      if (
        error instanceof ApiError &&
        error.status === 401 &&
        query.queryKey[1] !== "identity"
      ) {
        void queryClient.invalidateQueries({ queryKey: ["v1", "identity"] });
      }
    },
  }),
  defaultOptions: {
    queries: {
      staleTime: 15000,
      retry: (count, error) =>
        !(error instanceof ApiError && error.status < 500) && count < 1,
      refetchOnWindowFocus: true,
    },
    mutations: { retry: false },
  },
});
export function useIdentity() {
  const identity = useQuery({
    queryKey: ["v1", "identity"],
    queryFn: async ({ signal }) => {
      try {
        const data = await get<Identity>("/auth/me", signal);
        setReplayContext(data.user.id, data.company.id);
        return data;
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) clearReplayContext();
        throw error;
      }
    },
    retry: false,
  });
  // Also synchronize identities seeded by login/switch or the query cache.
  useEffect(() => {
    if (identity.error instanceof ApiError && identity.error.status === 401) clearReplayContext();
    else if (identity.data) setReplayContext(identity.data.user.id, identity.data.company.id);
  }, [identity.data, identity.error]);
  return identity;
}
export function useResource<T>(key: unknown[], path: string, enabled = true) {
  const identity = useIdentity();
  return useQuery({
    queryKey: ["v1", identity.data?.company.id, ...key],
    queryFn: ({ signal }) => get<T>(path, signal),
    enabled: enabled && !!identity.data,
  });
}
export async function refreshData() {
  await queryClient.invalidateQueries({ queryKey: ["v1"] });
}
