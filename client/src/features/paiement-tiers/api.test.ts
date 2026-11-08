import { beforeEach, describe, expect, it, vi } from "vitest";
import api from "@/lib/api";
import {
  creerLienTiers, demarrerPaiementTiers, desactiverLienTiers, lireApercuTiers, lireDemandeTiers, lireStatutTiers,
} from "./api";

vi.mock("@/lib/api", () => ({ default: { get: vi.fn(), post: vi.fn(), delete: vi.fn() } }));

describe("paiement par un tiers", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    for (const m of [api.get, api.post, api.delete]) vi.mocked(m).mockResolvedValue({ data: { active: true, url: "https://pay" } });
  });

  it("le voyageur crée, lit et désactive son lien", async () => {
    await lireDemandeTiers("r1");
    expect(api.get).toHaveBeenLastCalledWith("/v1/paiements/reservations/r1/demande-tiers/");
    await expect(creerLienTiers("r1")).resolves.toMatchObject({ active: true });
    expect(api.post).toHaveBeenLastCalledWith("/v1/paiements/reservations/r1/demande-tiers/");
    await desactiverLienTiers("r1");
    expect(api.delete).toHaveBeenLastCalledWith("/v1/paiements/reservations/r1/demande-tiers/");
  });

  it("le payeur lit le séjour, paie et suit son paiement", async () => {
    await lireApercuTiers("abc_DEF-123");
    expect(api.get).toHaveBeenLastCalledWith("/v1/paiements/tiers/abc_DEF-123/");
    await expect(demarrerPaiementTiers("abc_DEF-123", "mobile_money")).resolves.toBe("https://pay");
    expect(api.post).toHaveBeenLastCalledWith("/v1/paiements/tiers/abc_DEF-123/", { moyen: "mobile_money" });
    await lireStatutTiers("d1");
    expect(api.get).toHaveBeenLastCalledWith("/v1/paiements/tiers/demandes/d1/statut/");
  });

  it("garde le lien de l'adresse dans un seul segment", async () => {
    await lireApercuTiers("../../admin/x?");
    expect(api.get).toHaveBeenLastCalledWith("/v1/paiements/tiers/..%2F..%2Fadmin%2Fx%3F/");
  });
});
