import api from "@/lib/api";
import { urlProxy } from "@/lib/api-url";
import type { ActivityDetail, ActivityFilters, ActivityPage } from "./types";

const ACTIVITY = "/v1/admin/activity";

export function activityParams(filters: ActivityFilters, before?: number | null): Record<string, string> {
  const params: Record<string, string> = { period: filters.period, level: filters.level };
  for (const key of ["q", "category", "actor", "ip", "target_kind", "target_id"] as const) {
    if (filters[key]) params[key] = filters[key];
  }
  if (before) params.before = String(before);
  return params;
}

export async function listActivity(filters: ActivityFilters, before?: number | null) {
  return (await api.get<ActivityPage>(`${ACTIVITY}/`, { params: activityParams(filters, before) })).data;
}

export async function readActivity(id: number) {
  return (await api.get<ActivityDetail>(`${ACTIVITY}/${id}/`)).data;
}

export function activityExportUrl(filters: ActivityFilters) {
  return `${urlProxy(`${ACTIVITY}/export/`)}?${new URLSearchParams(activityParams(filters)).toString()}`;
}
