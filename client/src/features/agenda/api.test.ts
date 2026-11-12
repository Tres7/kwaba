import { beforeEach, describe, expect, it, vi } from "vitest";
import api from "@/lib/api";
import * as agenda from "./api";

vi.mock("@/lib/api", () => ({ default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() } }));

describe("agenda", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    for (const method of [api.get, api.post, api.put, api.delete]) {
      vi.mocked(method).mockResolvedValue({ data: { results: [], slots: [] } });
    }
  });

  it("reads and saves the availability", async () => {
    await agenda.readAvailability();
    expect(api.get).toHaveBeenLastCalledWith("/v1/agenda/availability/");
    const week = { cities: ["Lomé"], weekly_slots: [{ weekday: 0, start: "08:00", end: "12:00" }] };
    await agenda.saveWeek(week);
    expect(api.put).toHaveBeenLastCalledWith("/v1/agenda/availability/", week);
    await agenda.addException({ day: "2026-11-20", kind: "block" });
    expect(api.post).toHaveBeenLastCalledWith("/v1/agenda/availability/exceptions/", { day: "2026-11-20", kind: "block" });
    await agenda.deleteException(3);
    expect(api.delete).toHaveBeenLastCalledWith("/v1/agenda/availability/exceptions/3/");
    await agenda.setDayLimit("2026-11-20", 5);
    expect(api.put).toHaveBeenLastCalledWith("/v1/agenda/availability/day-limits/2026-11-20/", { max_visits: 5 });
  });

  it("lists and acts on the appointments", async () => {
    await agenda.listAppointments({ start: "2026-11-09", end: "2026-11-15", agent: "all" });
    expect(api.get).toHaveBeenLastCalledWith("/v1/agenda/appointments/",
      { params: { start: "2026-11-09", end: "2026-11-15", agent: "all" } });
    await agenda.readAppointment("a1");
    expect(api.get).toHaveBeenLastCalledWith("/v1/agenda/appointments/a1/");
    await agenda.onTheWay("a1");
    expect(api.post).toHaveBeenLastCalledWith("/v1/agenda/appointments/a1/on-the-way/");
    await agenda.cancelAppointment("a1", "Malade");
    expect(api.post).toHaveBeenLastCalledWith("/v1/verifications/appointments/a1/cancel/", { reason: "Malade" });
    await agenda.reassignAppointment("a1", "u2");
    expect(api.post).toHaveBeenLastCalledWith("/v1/verifications/appointments/a1/reassign/", { agent_id: "u2" });
    await agenda.bookByPhone("l1", "2026-11-20T09:00:00Z");
    expect(api.post).toHaveBeenLastCalledWith("/v1/verifications/listings/l1/appointment/",
      { start: "2026-11-20T09:00:00Z" });
    expect(agenda.appointmentIcsUrl("a1")).toBe("/api/proxy/v1/agenda/appointments/a1/ics");
  });

  it("calendar feed and admin views", async () => {
    await agenda.readFeed();
    expect(api.get).toHaveBeenLastCalledWith("/v1/agenda/feed/");
    await agenda.regenerateFeed();
    expect(api.post).toHaveBeenLastCalledWith("/v1/agenda/feed/");
    await agenda.readCoverage();
    expect(api.get).toHaveBeenLastCalledWith("/v1/agenda/admin/coverage/");
    await agenda.listAgents();
    expect(api.get).toHaveBeenLastCalledWith("/v1/agenda/admin/agents/");
    await agenda.readAgendaSettings();
    expect(api.get).toHaveBeenLastCalledWith("/v1/admin/agenda/settings/");
    await agenda.saveAgendaSettings({ notice_hours: 48 });
    expect(api.put).toHaveBeenLastCalledWith("/v1/admin/agenda/settings/", { notice_hours: 48 });
  });

  it("the host books and moves their visit", async () => {
    await agenda.readMyVisit();
    expect(api.get).toHaveBeenLastCalledWith("/v1/verifications/visit/");
    await agenda.listFreeSlots(["l1", "l2"]);
    expect(api.get).toHaveBeenLastCalledWith("/v1/verifications/visit/slots/", { params: { listings: "l1,l2" } });
    await agenda.bookVisit(["l1"], "2026-11-20T09:00:00Z");
    expect(api.post).toHaveBeenLastCalledWith("/v1/verifications/visit/book/",
      { listings: ["l1"], start: "2026-11-20T09:00:00Z" });
    await agenda.listMoveSlots("a1");
    expect(api.get).toHaveBeenLastCalledWith("/v1/verifications/visit/appointments/a1/slots/");
    await agenda.moveVisit("a1", "2026-11-21T09:00:00Z");
    expect(api.post).toHaveBeenLastCalledWith("/v1/verifications/visit/appointments/a1/move/",
      { start: "2026-11-21T09:00:00Z" });
  });
});
