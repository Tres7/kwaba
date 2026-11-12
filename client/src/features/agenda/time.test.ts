import { describe, expect, it } from "vitest";

const nb = (text: string) => text.replace(/ /g, "\u00a0");
import type { Appointment } from "./types";
import {
  addDays, addMonths, byDay, dayKey, durationMinutes, formatDuration, hourMinute, hoursShown, inTime, rangeMinutes, itineraryUrl, minutesOfDay, monthGrid,
  slotsByDay, visitStates, weekDays, weekStart, weekday,
} from "./time";

const appointment = (id: string, start: string, end: string, status: Appointment["status"] = "confirmed"): Appointment => ({
  id, title: "Studio", city: "Lomé", address: "", start, end, status, origin: "host", on_the_way_at: null, listings: [], agent: null,
  cancellation_reason: "", closing_reason: "", post_check: false,
});

describe("dates in Lomé", () => {
  it("reads the day and the hour in Africa/Lome", () => {
    expect(dayKey("2026-11-11T23:30:00Z")).toBe("2026-11-11");
    expect(dayKey("2026-11-11T23:30:00-02:00")).toBe("2026-11-12");
    expect(hourMinute("2026-11-11T09:05:00Z")).toBe("09:05");
    expect(minutesOfDay("2026-11-11T11:30:00Z")).toBe(690);
    expect(durationMinutes("2026-11-11T09:00:00Z", "2026-11-11T10:20:00Z")).toBe(80);
  });

  it("weeks start on Monday", () => {
    expect(weekday("2026-11-09")).toBe(0);
    expect(weekday("2026-11-15")).toBe(6);
    expect(weekStart("2026-11-11")).toBe("2026-11-09");
    expect(weekDays("2026-11-09")).toEqual(["2026-11-09", "2026-11-10", "2026-11-11", "2026-11-12", "2026-11-13",
      "2026-11-14", "2026-11-15"]);
    expect(addDays("2026-12-31", 1)).toBe("2027-01-01");
  });

  it("month grid of six weeks from the Monday before the first day", () => {
    const grid = monthGrid("2026-11-18");
    expect(grid).toHaveLength(42);
    expect(grid[0]).toBe("2026-10-26");
    expect(addMonths("2026-11-18", 1)).toBe("2026-12-01");
    expect(addMonths("2026-01-31", -1)).toBe("2025-12-01");
  });
});

describe("visits of the day", () => {
  it("groups by day and sorts by hour", () => {
    const days = byDay([appointment("b", "2026-11-11T14:30:00Z", "2026-11-11T15:30:00Z"),
      appointment("a", "2026-11-11T09:00:00Z", "2026-11-11T10:00:00Z"),
      appointment("c", "2026-11-12T09:00:00Z", "2026-11-12T10:00:00Z")]);
    expect(Object.keys(days)).toEqual(["2026-11-11", "2026-11-12"]);
    expect(days["2026-11-11"].map((a) => a.id)).toEqual(["a", "b"]);
  });

  it("the next visit is the first confirmed one not finished yet", () => {
    const states = visitStates([
      appointment("done", "2026-11-11T09:00:00Z", "2026-11-11T10:00:00Z", "done"),
      appointment("missed", "2026-11-11T10:00:00Z", "2026-11-11T11:00:00Z"),
      appointment("later", "2026-11-11T14:30:00Z", "2026-11-11T15:30:00Z"),
      appointment("next", "2026-11-11T11:30:00Z", "2026-11-11T12:30:00Z"),
      appointment("off", "2026-11-11T12:00:00Z", "2026-11-11T13:00:00Z", "cancelled"),
    ], new Date("2026-11-11T11:15:00Z"));
    expect(states).toEqual({ done: "done", missed: "past", later: "upcoming", next: "next", off: "cancelled" });
  });

  it("durations in hours, minutes only under an hour", () => {
    expect(formatDuration(30)).toBe(nb("30 min"));
    expect(formatDuration(60)).toBe(nb("1 h"));
    expect(formatDuration(80)).toBe(nb("1 h 20"));
    expect(formatDuration(140)).toBe(nb("2 h 20"));
    expect(formatDuration(125)).toBe(nb("2 h 05"));
    expect(formatDuration(120)).toBe(nb("2 h"));
  });

  it("says how long until the visit", () => {
    expect(inTime(40)).toBe("dans " + nb("40 min"));
    expect(inTime(150)).toBe("dans " + nb("2 h 30"));
    expect(inTime(120)).toBe("dans " + nb("2 h"));
    expect(inTime(60 * 50)).toBe("dans 2 jours");
    expect(inTime(-5)).toBe("maintenant");
  });

  it("itinerary to the measured position, or to the address", () => {
    expect(itineraryUrl({ latitude: 6.13, longitude: 1.22 }, "Bè", "Lomé"))
      .toBe("https://www.google.com/maps/dir/?api=1&destination=6.13%2C1.22");
    expect(itineraryUrl(null, "Bè Kpota", "Lomé"))
      .toBe(`https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent("Bè Kpota, Lomé, Togo")}`);
  });

  it("free slots grouped by day", () => {
    expect(slotsByDay(["2026-11-12T09:00:00Z", "2026-11-11T15:00:00Z", "2026-11-11T09:00:00Z"])).toEqual([
      ["2026-11-11", ["2026-11-11T09:00:00Z", "2026-11-11T15:00:00Z"]],
      ["2026-11-12", ["2026-11-12T09:00:00Z"]],
    ]);
  });
});

describe("planning timeline", () => {
  it("minutes of a range within the day", () => {
    expect(rangeMinutes({ start: "2026-11-20T08:00:00Z", end: "2026-11-20T12:30:00Z" }, "2026-11-20")).toEqual([480, 750]);
    expect(rangeMinutes({ start: "2026-11-20T00:00:00Z", end: "2026-11-21T00:00:00Z" }, "2026-11-20")).toEqual([0, 1440]);
  });

  it("hours shown cover every visit and window, whole-day blocks aside", () => {
    expect(hoursShown([])).toEqual([7, 19]);
    expect(hoursShown([[360, 600], [1080, 1230]])).toEqual([6, 21]);
    expect(hoursShown([[0, 1440]])).toEqual([7, 19]);
  });
});
