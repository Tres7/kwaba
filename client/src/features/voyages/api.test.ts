import { beforeEach, describe, expect, it, vi } from "vitest";
import api from "@/lib/api";
import * as voyages from "./api";

vi.mock("@/lib/api", () => ({ default: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() } }));

describe("voyages", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    for (const m of [api.get, api.post, api.patch, api.delete]) vi.mocked(m).mockResolvedValue({ data: { id: "v1", results: [{ id: "r1" }] } });
  });

  it("liste et lit", async () => {
    await expect(voyages.listerVoyages()).resolves.toEqual([{ id: "r1" }]);
    expect(api.get).toHaveBeenLastCalledWith("/v1/voyages/");
    await voyages.lireVoyage("v1");
    expect(api.get).toHaveBeenLastCalledWith("/v1/voyages/v1/");
    await voyages.lireInvitation("CODE");
    expect(api.get).toHaveBeenLastCalledWith("/v1/voyages/invitations/CODE/");
  });

  it("crée, modifie, supprime", async () => {
    await voyages.creerVoyage({ nom: "Lomé" });
    expect(api.post).toHaveBeenLastCalledWith("/v1/voyages/", { nom: "Lomé" });
    await voyages.modifierVoyage("v1", { notes: "Rendez-vous" });
    expect(api.patch).toHaveBeenLastCalledWith("/v1/voyages/v1/", { notes: "Rendez-vous" });
    await voyages.supprimerVoyage("v1");
    expect(api.delete).toHaveBeenLastCalledWith("/v1/voyages/v1/");
  });

  it("propositions et votes", async () => {
    await voyages.proposerLogement("v1", "h1");
    expect(api.post).toHaveBeenLastCalledWith("/v1/voyages/v1/propositions/", { hebergement: "h1" });
    await voyages.retirerProposition("v1", 5);
    expect(api.delete).toHaveBeenLastCalledWith("/v1/voyages/v1/propositions/5/");
    await voyages.voter("v1", 5);
    expect(api.post).toHaveBeenLastCalledWith("/v1/voyages/v1/vote/", { proposition: 5 });
    await voyages.retirerVote("v1");
    expect(api.delete).toHaveBeenLastCalledWith("/v1/voyages/v1/vote/");
    await voyages.retenirProposition("v1", 5);
    expect(api.post).toHaveBeenLastCalledWith("/v1/voyages/v1/retenir/", { proposition: 5 });
  });

  it("étapes, réservations partagées, membres", async () => {
    await voyages.ajouterEtape("v1", { titre: "Plage", heure: null });
    expect(api.post).toHaveBeenLastCalledWith("/v1/voyages/v1/etapes/", { titre: "Plage", heure: null });
    await voyages.retirerEtape("v1", 8);
    expect(api.delete).toHaveBeenLastCalledWith("/v1/voyages/v1/etapes/8/");
    await voyages.partagerReservation("v1", "r1");
    expect(api.post).toHaveBeenLastCalledWith("/v1/voyages/v1/reservations/", { reservation: "r1" });
    await voyages.retirerReservation("v1", 9);
    expect(api.delete).toHaveBeenLastCalledWith("/v1/voyages/v1/reservations/9/");
    await voyages.retirerMembre("v1", "m1");
    expect(api.delete).toHaveBeenLastCalledWith("/v1/voyages/v1/membres/m1/");
    await voyages.nouveauLien("v1");
    expect(api.post).toHaveBeenLastCalledWith("/v1/voyages/v1/nouveau-lien/");
  });

  it("rejoint un voyage par son invitation", async () => {
    await expect(voyages.rejoindre("CODE")).resolves.toMatchObject({ id: "v1" });
    expect(api.post).toHaveBeenLastCalledWith("/v1/voyages/invitations/CODE/");
  });

  it("cherche des logements pour le groupe", async () => {
    await voyages.chercherLogements({ q: "Lomé", limit: 12 });
    expect(api.get).toHaveBeenLastCalledWith("/v1/hebergements/", { params: { q: "Lomé", limit: 12 } });
  });
});
