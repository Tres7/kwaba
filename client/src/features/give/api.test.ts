import { beforeEach, describe, expect, it, vi } from "vitest";
import api from "@/lib/api";
import {
  creerOng, creerProjet, demarrerDon, depublierOng, effectuerReversement, lireConfig, lireDon, lireImpact, lireOrganisation,
  listerMesDons, listerOngAdmin, listerOrganisations, listerProjetsAdmin, modifierOng, modifierProjet, preparerReversements,
} from "./api";

vi.mock("@/lib/api", () => ({ default: { get: vi.fn(), post: vi.fn(), patch: vi.fn() } }));

const MULTIPART = { headers: { "Content-Type": "multipart/form-data" } };

describe("give", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.get).mockResolvedValue({ data: { results: [] } });
    vi.mocked(api.post).mockResolvedValue({ data: { id: "d1", url: "https://paiement", dons: 2 } });
  });

  it.each([
    [lireConfig, [], "/v1/give/config/"],
    [lireImpact, [], "/v1/give/impact/"],
    [lireOrganisation, ["ong-togo"], "/v1/give/organisations/ong-togo/"],
    [lireDon, ["d1"], "/v1/give/dons/d1/"],
    [listerMesDons, [], "/v1/give/dons/"],
    [listerOngAdmin, [], "/v1/admin/give/organisations/"],
    [listerProjetsAdmin, ["o4"], "/v1/admin/give/organisations/o4/projets/"],
  ])("lit %o", async (fonction, parametres, chemin) => {
    await (fonction as (...args: unknown[]) => Promise<unknown>)(...parametres);
    expect(api.get).toHaveBeenCalledWith(chemin);
  });

  it("filtre les ONG par cause, seulement si une cause est choisie", async () => {
    await listerOrganisations("eau");
    expect(api.get).toHaveBeenLastCalledWith("/v1/give/organisations/", { params: { cause: "eau" } });
    await listerOrganisations(null);
    expect(api.get).toHaveBeenLastCalledWith("/v1/give/organisations/", { params: {} });
  });

  it("démarre un don et renvoie la page de paiement", async () => {
    const don = { organisation: "ong", projet: null, montant: 1000, couvre_frais: true, moyen: "carte", partage_identite: false };
    await expect(demarrerDon(don)).resolves.toMatchObject({ url: "https://paiement" });
    expect(api.post).toHaveBeenCalledWith("/v1/give/dons/", don);
  });

  it("envoie les fichiers en multipart", async () => {
    const corps = new FormData();
    await creerOng(corps);
    expect(api.post).toHaveBeenLastCalledWith("/v1/admin/give/organisations/", corps, MULTIPART);
    await modifierOng("o4", corps);
    expect(api.patch).toHaveBeenLastCalledWith("/v1/admin/give/organisations/o4/", corps, MULTIPART);
    await creerProjet("o4", corps);
    expect(api.post).toHaveBeenLastCalledWith("/v1/admin/give/organisations/o4/projets/", corps, MULTIPART);
    await modifierProjet("p9", corps);
    expect(api.patch).toHaveBeenLastCalledWith("/v1/admin/give/projets/p9/", corps, MULTIPART);
    await effectuerReversement(7, corps);
    expect(api.post).toHaveBeenLastCalledWith("/v1/admin/give/reversements/7/effectuer/", corps, MULTIPART);
  });

  it("dépublie une ONG en JSON : le multipart ne sait pas envoyer une date vide", async () => {
    await depublierOng("o4");
    expect(api.patch).toHaveBeenCalledWith("/v1/admin/give/organisations/o4/", { verifiee_le: null });
  });

  it("prépare les reversements", async () => {
    await expect(preparerReversements()).resolves.toMatchObject({ dons: 2 });
    expect(api.post).toHaveBeenCalledWith("/v1/admin/give/reversements/preparer/");
  });
});
