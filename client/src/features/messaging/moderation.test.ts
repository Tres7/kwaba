import { describe, expect, it } from "vitest";
import { checkFor, isSuspended, moderationFailure } from "./moderation";

const failure = (data: unknown) => ({ response: { data } });

describe("moderation", () => {
  it("reads refusals and confirmation requests from the API", () => {
    expect(moderationFailure(failure({ code: "abusive_content", categories: ["insult"] })))
      .toEqual({ code: "abusive_content", categories: ["insult"] });
    expect(moderationFailure(failure({ code: "confirmation_required", categories: ["threat"] })))
      .toEqual({ code: "confirmation_required", categories: ["threat"] });
    expect(moderationFailure(failure({ code: "messaging_suspended", until: "2026-11-12T10:00:00Z" })))
      .toEqual({ code: "messaging_suspended", until: "2026-11-12T10:00:00Z" });
  });

  it("ignores other errors so the send button stays usable", () => {
    expect(moderationFailure(failure({ detail: "Erreur" }))).toBeNull();
    expect(moderationFailure(new Error("network"))).toBeNull();
  });

  it("applies a check only to the text it was made for", () => {
    const check = { text: "tu es nul", level: "block" as const, categories: ["insult" as const] };
    expect(checkFor(check, " tu es nul ")).toEqual(check);
    expect(checkFor(check, "tu es nul en maths")).toBeNull();
    expect(checkFor(null, "texte")).toBeNull();
  });

  it("tells whether a suspension is still running", () => {
    const now = Date.parse("2026-11-12T10:00:00Z");
    expect(isSuspended("2026-11-12T11:00:00Z", now)).toBe(true);
    expect(isSuspended("2026-11-12T09:00:00Z", now)).toBe(false);
    expect(isSuspended(null, now)).toBe(false);
  });
});
