import { beforeEach, describe, expect, it, vi } from "vitest";
import api from "@/lib/api";
import * as transferts from "./api";

vi.mock("@/lib/api", () => ({ default: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), put: vi.fn(), delete: vi.fn() } }));

describe("transferts", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    for (const m of [api.get, api.post, api.delete]) vi.mocked(m).mockResolvedValue({ data: { id: "t1", results: [{ id: "t1" }], code: "LFW" } });
  });

  it("lit les transferts, les aéroports et le séjour lié", async () => {
    await expect(transferts.listerMesTransferts()).resolves.toEqual([{ id: "t1" }]);
    expect(api.get).toHaveBeenLastCalledWith("/v1/transferts/");
    await transferts.lireTransfert("t1");
    expect(api.get).toHaveBeenLastCalledWith("/v1/transferts/t1/");
    await transferts.listerAeroports();
    expect(api.get).toHaveBeenLastCalledWith("/v1/transferts/aeroports/");
  });

  it("calcule un devis", async () => {
    const params = { aeroport: "LFW", arrivee: "2026-12-01T10:00", passagers: 2, bagages: 1 };
    await transferts.calculerDevis(params);
    expect(api.get).toHaveBeenCalledWith("/v1/transferts/devis/", { params });
  });

  it("crée et annule un transfert", async () => {
    await transferts.creerTransfert({ aeroport: "LFW" });
    expect(api.post).toHaveBeenLastCalledWith("/v1/transferts/", { aeroport: "LFW" });
    await transferts.annulerTransfert("t1");
    expect(api.delete).toHaveBeenLastCalledWith("/v1/transferts/t1/");
    expect(transferts.adresseCompteRemboursement("t1")).toBe("/v1/transferts/t1/compte-remboursement/");
  });

  it("gère les aéroports et les tarifs", async () => {
    await transferts.listerAeroportsAdmin();
    expect(api.get).toHaveBeenLastCalledWith("/v1/admin/transferts/aeroports/");
    await expect(transferts.creerAeroport({ nom: "Lomé" })).resolves.toMatchObject({ code: "LFW" });
    expect(api.post).toHaveBeenLastCalledWith("/v1/admin/transferts/aeroports/", { nom: "Lomé" });
    await transferts.modifierAeroport("LFW", { nom: "Lomé" });
    expect(api.patch).toHaveBeenLastCalledWith("/v1/admin/transferts/aeroports/LFW/", { nom: "Lomé" });
    await transferts.enregistrerTarifs("LFW", [{ categorie: "berline" }]);
    expect(api.put).toHaveBeenLastCalledWith("/v1/admin/transferts/aeroports/LFW/tarifs/", [{ categorie: "berline" }]);
  });

  it("gère les chauffeurs et les attributions", async () => {
    await transferts.listerChauffeurs();
    expect(api.get).toHaveBeenLastCalledWith("/v1/admin/transferts/chauffeurs/");
    await transferts.creerChauffeur({ nom: "Kodjo" });
    expect(api.post).toHaveBeenLastCalledWith("/v1/admin/transferts/chauffeurs/", { nom: "Kodjo" });
    await transferts.modifierChauffeur(4 as never, { nom: "Kodjo" });
    expect(api.patch).toHaveBeenLastCalledWith("/v1/admin/transferts/chauffeurs/4/", { nom: "Kodjo" });
    await transferts.listerChauffeursDisponibles("t1");
    expect(api.get).toHaveBeenLastCalledWith("/v1/admin/transferts/transferts/t1/chauffeurs/");
    await transferts.attribuerChauffeur("t1", 4);
    expect(api.post).toHaveBeenLastCalledWith("/v1/admin/transferts/transferts/t1/attribuer/", { chauffeur: 4 });
    await transferts.annulerTransfertAdmin("t1", "Vol annulé");
    expect(api.post).toHaveBeenLastCalledWith("/v1/admin/transferts/transferts/t1/annuler/", { motif: "Vol annulé" });
  });
});
