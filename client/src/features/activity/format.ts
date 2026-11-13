import type { ActivityEntry } from "./types";

export const TIMEZONE = "Africa/Lome";
const KEY = new Intl.DateTimeFormat("en-CA", { timeZone: TIMEZONE, year: "numeric", month: "2-digit", day: "2-digit" });
const DAY = new Intl.DateTimeFormat("fr-FR", { timeZone: TIMEZONE, weekday: "long", day: "numeric", month: "long" });
const TIME = new Intl.DateTimeFormat("fr-FR", { timeZone: TIMEZONE, hour: "2-digit", minute: "2-digit" });
const FULL = new Intl.DateTimeFormat("fr-FR", {
  timeZone: TIMEZONE, weekday: "long", day: "numeric", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit",
});

export const dayKey = (moment: string | Date) => KEY.format(typeof moment === "string" ? new Date(moment) : moment);
export const clockTime = (moment: string) => TIME.format(new Date(moment));
export const fullDate = (moment: string) => FULL.format(new Date(moment));

export interface DayGroup {
  key: string;
  title: string;
  subtitle: string;
  entries: ActivityEntry[];
}

export function groupByDay(entries: ActivityEntry[], now: Date): DayGroup[] {
  const today = dayKey(now);
  const yesterday = dayKey(new Date(now.getTime() - 86_400_000));
  const groups: DayGroup[] = [];
  for (const entry of entries) {
    const key = dayKey(entry.created_at);
    let group = groups[groups.length - 1];
    if (!group || group.key !== key) {
      const day = DAY.format(new Date(entry.created_at));
      const title = key === today ? "Aujourd'hui" : key === yesterday ? "Hier" : day.charAt(0).toUpperCase() + day.slice(1);
      group = { key, title, subtitle: key === today || key === yesterday ? day : "", entries: [] };
      groups.push(group);
    }
    group.entries.push(entry);
  }
  return groups;
}

export function initials(name: string): string {
  const words = name.replace(/@.*/, "").split(/[\s._-]+/).filter(Boolean);
  return (words.length > 1 ? words[0][0] + words[words.length - 1][0] : (words[0] ?? "?").slice(0, 2)).toUpperCase();
}
