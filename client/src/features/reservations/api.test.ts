import { beforeEach, describe, expect, it, vi } from "vitest";
import api from "@/lib/api";
import { annulerReservation, annulerReservationAdmin, creerReservation, lireReservation, listerMesReservations } from "./api";

vi.mock("@/lib/api", () => ({ default: { get: vi.fn(), post: vi.fn(), delete: vi.fn() } }));

describe("reservations", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    for (const m of [api.get, api.post, api.delete]) vi.mocked(m).mockResolvedValue({ data: { id: "r1", results: [{ id: "r1" }], rembourse: 1000 } });
  });

  it("liste et lit", async () => {
    await expect(listerMesReservations()).resolves.toEqual([{ id: "r1" }]);
    expect(api.get).toHaveBeenLastCalledWith("/v1/reservations/");
    await lireReservation("r1");
    expect(api.get).toHaveBeenLastCalledWith("/v1/reservations/r1/");
  });

  it("transmet le total attendu : le serveur refuse si le prix a changé", async () => {
    const corps = { hebergement: "h1", check_in: "2026-12-01", check_out: "2026-12-03", total_attendu: 50000 };
    await creerReservation(corps);
    expect(api.post).toHaveBeenCalledWith("/v1/reservations/", corps);
  });

  it("annule et renvoie le remboursement", async () => {
    await expect(annulerReservation("r1")).resolves.toMatchObject({ rembourse: 1000 });
    expect(api.delete).toHaveBeenCalledWith("/v1/reservations/r1/");
  });

  it("annule côté back-office avec un motif", async () => {
    await annulerReservationAdmin("r1", "Doublon");
    expect(api.post).toHaveBeenCalledWith("/v1/admin/reservations/r1/annuler/", { motif: "Doublon" });
  });
});
