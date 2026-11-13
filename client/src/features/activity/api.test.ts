import { beforeEach, describe, expect, it, vi } from "vitest";
import api from "@/lib/api";
import * as activity from "./api";
import type { ActivityFilters } from "./types";

vi.mock("@/lib/api", () => ({ default: { get: vi.fn() } }));

const FILTERS: ActivityFilters = {
  q: "", period: "7d", level: "important", category: "", actor: "", ip: "", target_kind: "", target_id: "",
};

describe("activity", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.get).mockResolvedValue({ data: {} });
  });

  it("lists with only the filters that are set", async () => {
    await activity.listActivity(FILTERS);
    expect(api.get).toHaveBeenLastCalledWith("/v1/admin/activity/", { params: { period: "7d", level: "important" } });
    await activity.listActivity({ ...FILTERS, q: "Jean", category: "rights", ip: "41.0.0.1" }, 120);
    expect(api.get).toHaveBeenLastCalledWith("/v1/admin/activity/", {
      params: { period: "7d", level: "important", q: "Jean", category: "rights", ip: "41.0.0.1", before: "120" },
    });
  });

  it("reads one event and builds the export address", async () => {
    await activity.readActivity(5);
    expect(api.get).toHaveBeenLastCalledWith("/v1/admin/activity/5/");
    expect(activity.activityExportUrl({ ...FILTERS, level: "sensitive" }))
      .toBe("/api/proxy/v1/admin/activity/export?period=7d&level=sensitive");
  });
});
