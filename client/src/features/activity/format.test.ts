import { describe, expect, it } from "vitest";
import { groupByDay, initials } from "./format";
import type { ActivityEntry } from "./types";

const entry = (id: number, created_at: string) => ({ id, created_at } as ActivityEntry);

describe("activity format", () => {
  it("groups by day, newest first, with today and yesterday named", () => {
    const groups = groupByDay([
      entry(3, "2026-11-13T17:56:00Z"), entry(2, "2026-11-13T09:00:00Z"), entry(1, "2026-11-12T19:02:00Z"),
      entry(0, "2026-11-10T08:00:00Z"),
    ], new Date("2026-11-13T20:00:00Z"));
    expect(groups.map((g) => [g.title, g.entries.length])).toEqual([["Aujourd'hui", 2], ["Hier", 1], ["Mardi 10 novembre", 1]]);
    expect(groups[0].subtitle).toBe("vendredi 13 novembre");
  });

  it("initials of a name or an email", () => {
    expect(initials("Awa Traoré")).toBe("AT");
    expect(initials("jean.kouame@example.com")).toBe("JK");
    expect(initials("Koffi")).toBe("KO");
  });
});
