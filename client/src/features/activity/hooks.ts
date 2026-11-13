import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { listActivity, readActivity } from "./api";
import type { ActivityFilters } from "./types";

export const activityKeys = {
  all: ["admin", "activity"] as const,
  list: (filters: ActivityFilters) => [...activityKeys.all, "list", filters] as const,
  entry: (id: number) => [...activityKeys.all, "entry", id] as const,
};

export function useActivity(filters: ActivityFilters) {
  return useInfiniteQuery({
    queryKey: activityKeys.list(filters),
    queryFn: ({ pageParam }) => listActivity(filters, pageParam),
    initialPageParam: null as number | null,
    getNextPageParam: (last) => last.next,
    refetchInterval: 60_000,
  });
}

export function useActivityEntry(id: number | null) {
  return useQuery({ queryKey: activityKeys.entry(id ?? 0), queryFn: () => readActivity(id ?? 0), enabled: !!id });
}
