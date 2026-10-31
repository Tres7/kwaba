import { beforeEach, describe, expect, it, vi } from "vitest";
import api from "@/lib/api";
import { devenirHote, fermerMonCompte, lireMoi, lireStatsAdmin, modifierMoi, modifierUtilisateurAdmin } from "./api";

vi.mock("@/lib/api", () => ({ default: { get: vi.fn(), patch: vi.fn(), delete: vi.fn() } }));

describe("users", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    for (const m of [api.get, api.patch]) vi.mocked(m).mockResolvedValue({ data: { first_name: "Kossi" } });
  });

  it("lit et modifie son compte", async () => {
    await expect(lireMoi()).resolves.toEqual({ first_name: "Kossi" });
    expect(api.get).toHaveBeenLastCalledWith("/v1/users/me/");
    await modifierMoi({ first_name: "Ama", phone: null });
    expect(api.patch).toHaveBeenLastCalledWith("/v1/users/me/", { first_name: "Ama", phone: null });
  });

  it("devient hôte et ferme son compte", async () => {
    await devenirHote();
    expect(api.patch).toHaveBeenLastCalledWith("/v1/users/me/", { role: "hote" });
    await fermerMonCompte();
    expect(api.delete).toHaveBeenCalledWith("/v1/users/me/");
  });

  it("gère les comptes depuis le back-office", async () => {
    await modifierUtilisateurAdmin("u1", { is_active: false });
    expect(api.patch).toHaveBeenLastCalledWith("/v1/admin/users/u1/", { is_active: false });
    await lireStatsAdmin();
    expect(api.get).toHaveBeenLastCalledWith("/v1/admin/stats/");
  });
});
