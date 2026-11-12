import { describe, expect, it } from "vitest";
import { SECTIONS, afterMonday10, clock, durationOptions } from "./settingsHelp";
import type { AgendaSettingsValues } from "./types";

const DEFAULTS: AgendaSettingsValues = {
  notice_hours: 24, horizon_days: 14, max_per_day: 4, margin_minutes: 30, visit_minutes: 60,
  extra_listing_minutes: 20, max_listings: 5, same_site_distance_m: 200, digest_hour: 18, decision_alert_hours: 2,
  host_reminder_days: 2, host_alert_days: 3,
};

const help = (key: keyof AgendaSettingsValues, values = DEFAULTS) =>
  SECTIONS.flatMap((s) => s.fields).find((f) => f.key === key)!.help(values);

describe("settings help", () => {
  it("clock times", () => {
    expect(clock(570)).toBe("9 h 30");
    expect(clock(600)).toBe("10 h");
    expect(clock(1500)).toBe("1 h");
  });

  it("notice from Monday at 10", () => {
    expect(afterMonday10(24)).toBe("le mardi à 10 h");
    expect(afterMonday10(1)).toBe("le lundi à 11 h");
    expect(afterMonday10(72)).toBe("le jeudi à 10 h");
  });

  it("concrete examples follow the values", () => {
    expect(help("notice_hours")).toContain("le mardi à 10 h");
    expect(help("visit_minutes")).toContain("se termine à 10 h");
    expect(help("visit_minutes", { ...DEFAULTS, visit_minutes: 80 })).toContain("10 h 20");
    expect(help("extra_listing_minutes")).toContain("1 h 40");
    expect(help("margin_minutes")).toContain("10 h 30");
    expect(help("margin_minutes", { ...DEFAULTS, margin_minutes: 0 })).toContain("Aucun écart");
    expect(help("max_listings")).toContain("2 h 20");
    expect(help("host_reminder_days")).toContain("le mercredi");
    expect(help("host_alert_days", { ...DEFAULTS, host_alert_days: 8 })).toContain("de la semaine suivante");
  });

  it("durations are chosen every five minutes", () => {
    expect(durationOptions(0, 20)).toEqual([0, 5, 10, 15, 20]);
  });
});
