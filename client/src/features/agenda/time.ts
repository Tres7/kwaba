import type { Appointment } from "./types";

export const TIMEZONE = "Africa/Lome";

const KEY_FORMAT = new Intl.DateTimeFormat("en-CA", { timeZone: TIMEZONE, year: "numeric", month: "2-digit", day: "2-digit" });
const TIME_FORMAT = new Intl.DateTimeFormat("en-GB", { timeZone: TIMEZONE, hour: "2-digit", minute: "2-digit", hourCycle: "h23" });

export function dayKey(moment: string | Date): string {
  return KEY_FORMAT.format(typeof moment === "string" ? new Date(moment) : moment);
}

function asUtcDate(key: string): Date {
  return new Date(`${key}T00:00:00Z`);
}

export function addDays(key: string, days: number): string {
  const date = asUtcDate(key);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

export function weekday(key: string): number {
  return (asUtcDate(key).getUTCDay() + 6) % 7;
}

export function weekStart(key: string): string {
  return addDays(key, -weekday(key));
}

export function weekDays(start: string): string[] {
  return Array.from({ length: 7 }, (_, i) => addDays(start, i));
}

export function monthGrid(key: string): string[] {
  const first = weekStart(`${key.slice(0, 8)}01`);
  return Array.from({ length: 42 }, (_, i) => addDays(first, i));
}

export function addMonths(key: string, months: number): string {
  const date = asUtcDate(`${key.slice(0, 8)}01`);
  date.setUTCMonth(date.getUTCMonth() + months);
  return date.toISOString().slice(0, 10);
}

export function hourMinute(moment: string): string {
  return TIME_FORMAT.format(new Date(moment));
}

export function minutesOfDay(moment: string): number {
  const [hours, minutes] = hourMinute(moment).split(":").map(Number);
  return hours * 60 + minutes;
}

export function durationMinutes(start: string, end: string): number {
  return Math.round((new Date(end).getTime() - new Date(start).getTime()) / 60_000);
}

export function byDay<T extends { start: string }>(items: T[]): Record<string, T[]> {
  const days: Record<string, T[]> = {};
  for (const item of [...items].sort((a, b) => a.start.localeCompare(b.start))) {
    (days[dayKey(item.start)] ??= []).push(item);
  }
  return days;
}

export type VisitState = "done" | "next" | "upcoming" | "past" | "cancelled";

export function visitStates(appointments: Appointment[], now: Date): Record<string, VisitState> {
  const states: Record<string, VisitState> = {};
  const nextVisit = [...appointments]
    .filter((a) => a.status === "confirmed" && new Date(a.end) > now)
    .sort((a, b) => a.start.localeCompare(b.start))[0];
  for (const a of appointments) {
    if (a.status === "cancelled") states[a.id] = "cancelled";
    else if (a.status === "done") states[a.id] = "done";
    else if (a.id === nextVisit?.id) states[a.id] = "next";
    else states[a.id] = new Date(a.end) <= now ? "past" : "upcoming";
  }
  return states;
}

export function minutesUntil(moment: string, now: Date): number {
  return Math.round((new Date(moment).getTime() - now.getTime()) / 60_000);
}

export function formatDuration(minutes: number): string {
  const total = Math.max(0, Math.round(minutes));
  if (total < 60) return `${total}\u00a0min`;
  const hours = Math.floor(total / 60);
  const rest = total % 60;
  return rest ? `${hours}\u00a0h\u00a0${String(rest).padStart(2, "0")}` : `${hours}\u00a0h`;
}

export function inTime(minutes: number): string {
  if (minutes <= 0) return "maintenant";
  if (minutes < 24 * 60) return `dans ${formatDuration(minutes)}`;
  const hours = Math.floor(minutes / 60);
  const days = Math.round(hours / 24);
  return `dans ${days} jour${days > 1 ? "s" : ""}`;
}

export function itineraryUrl(position: { latitude: number; longitude: number } | null, address: string, city: string) {
  const destination = position ? `${position.latitude},${position.longitude}` : `${address}, ${city}, Togo`;
  return `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(destination)}`;
}

export function slotsByDay(slots: string[]): [string, string[]][] {
  const days = byDay(slots.map((start) => ({ start })));
  return Object.entries(days).map(([key, items]) => [key, items.map((i) => i.start)]);
}
