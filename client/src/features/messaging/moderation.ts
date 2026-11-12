import type { ModerationCategory, ModerationCheck } from "./types";

export type ModerationFailure =
  | { code: "abusive_content" | "confirmation_required"; categories: ModerationCategory[] }
  | { code: "messaging_suspended"; until: string };

export function moderationFailure(err: unknown): ModerationFailure | null {
  const data = (err as { response?: { data?: { code?: string; categories?: ModerationCategory[]; until?: string } } }).response?.data;
  if (data?.code === "abusive_content" || data?.code === "confirmation_required") {
    return { code: data.code, categories: data.categories ?? [] };
  }
  if (data?.code === "messaging_suspended" && data.until) return { code: "messaging_suspended", until: data.until };
  return null;
}

export type DraftCheck = ModerationCheck & { text: string };

export function checkFor(check: DraftCheck | null, text: string): ModerationCheck | null {
  return check && check.text === text.trim() ? check : null;
}

export function isSuspended(until: string | null, now = Date.now()): boolean {
  return until !== null && new Date(until).getTime() > now;
}
