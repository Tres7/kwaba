export type ActivityCategory = "connections" | "rights" | "listings" | "agenda" | "money" | "moderation" | "objects" | "modules";
export type ActivityLevel = "sensitive" | "important" | "routine";
export type LevelFilter = "sensitive" | "important" | "all";
export type Period = "24h" | "7d" | "30d";

export interface ActivityPerson {
  id: string | null;
  name: string;
  email: string;
  role: string;
}

export interface ActivityTarget {
  kind: string;
  kind_label: string;
  id: string;
  label: string;
}

export interface ActivityEntry {
  id: number;
  created_at: string;
  action: string;
  label: string;
  category: ActivityCategory;
  category_label: string;
  level: ActivityLevel;
  summary: string;
  actor: ActivityPerson | null;
  ip: string | null;
  target: ActivityTarget | null;
  legacy: boolean;
}

export interface ActivityDetail extends ActivityEntry {
  details: { label: string; value: string }[];
}

export interface ActivityPage {
  results: ActivityEntry[];
  next: number | null;
  counts: Record<ActivityCategory, number>;
  today: { sensitive: number; blocked: number };
  categories: { code: ActivityCategory; label: string }[];
}

export interface ActivityFilters {
  q: string;
  period: Period;
  level: LevelFilter;
  category: ActivityCategory | "";
  actor: string;
  ip: string;
  target_kind: string;
  target_id: string;
}
