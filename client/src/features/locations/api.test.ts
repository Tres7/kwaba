import { beforeEach, describe, expect, it, vi } from "vitest";
import api from "@/lib/api";
import * as locations from "./api";

vi.mock("@/lib/api", () => ({ default: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), put: vi.fn(), delete: vi.fn() } }));

describe("locations", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    for (const m of [api.get, api.post, api.patch, api.delete]) vi.mocked(m).mockResolvedValue({ data: { id: 1, results: [{ id: "l1" }] } });
  });

  it("lit le catalogue, les chauffeurs et les réservations", async () => {
    await locations.lireCatalogue();
    expect(api.get).toHaveBeenLastCalledWith("/v1/locations/catalogue/");
    await locations.listerMesChauffeurs();
    expect(api.get).toHaveBeenLastCalledWith("/v1/locations/mes-chauffeurs/");
  });

  it("calcule un devis, crée, lit et annule une location", async () => {
    await locations.calculerDevisLocation({ categorie: 2 });
    expect(api.get).toHaveBeenLastCalledWith("/v1/locations/devis/", { params: { categorie: 2 } });
    await locations.creerLocation({ formule: "avec_chauffeur" });
    expect(api.post).toHaveBeenLastCalledWith("/v1/locations/", { formule: "avec_chauffeur" });
    await expect(locations.listerMesLocations()).resolves.toEqual([{ id: "l1" }]);
    expect(api.get).toHaveBeenLastCalledWith("/v1/locations/");
    await locations.lireLocation("l1");
    expect(api.get).toHaveBeenLastCalledWith("/v1/locations/l1/");
    await locations.annulerLocation("l1");
    expect(api.delete).toHaveBeenLastCalledWith("/v1/locations/l1/");
    expect(locations.adresseCompteRemboursement("l1")).toBe("/v1/locations/l1/compte-remboursement/");
  });

  it("gère les véhicules et leurs photos", async () => {
    await locations.listerCategories();
    expect(api.get).toHaveBeenLastCalledWith("/v1/admin/location/categories/");
    await locations.creerCategorie({ nom: "Berline" });
    expect(api.post).toHaveBeenLastCalledWith("/v1/admin/location/categories/", { nom: "Berline" });
    await locations.modifierCategorie(2, { nom: "Berline" });
    expect(api.patch).toHaveBeenLastCalledWith("/v1/admin/location/categories/2/", { nom: "Berline" });
    const corps = new FormData();
    await locations.ajouterPhoto(2, corps);
    expect(api.post).toHaveBeenLastCalledWith("/v1/admin/location/categories/2/photos/", corps, { headers: { "Content-Type": "multipart/form-data" } });
    await locations.rendrePrincipale(2, 9);
    expect(api.patch).toHaveBeenLastCalledWith("/v1/admin/location/categories/2/photos/9/", { principale: true });
    await locations.retirerPhoto(2, 9);
    expect(api.delete).toHaveBeenLastCalledWith("/v1/admin/location/categories/2/photos/9/");
  });

  it("gère les loueurs, les lieux et les règles", async () => {
    await locations.creerLoueur({ nom: "Auto" });
    expect(api.post).toHaveBeenLastCalledWith("/v1/admin/location/loueurs/", { nom: "Auto" });
    await locations.modifierLoueur(3, { nom: "Auto" });
    expect(api.patch).toHaveBeenLastCalledWith("/v1/admin/location/loueurs/3/", { nom: "Auto" });
    await locations.creerLieu({ nom: "Aéroport" });
    expect(api.post).toHaveBeenLastCalledWith("/v1/admin/location/lieux/", { nom: "Aéroport" });
    await locations.modifierLieu(4, { nom: "Gare" });
    expect(api.patch).toHaveBeenLastCalledWith("/v1/admin/location/lieux/4/", { nom: "Gare" });
    await locations.enregistrerRegles({ delai_min_jours: 2 });
    expect(api.put).toHaveBeenLastCalledWith("/v1/admin/location/regles/", { delai_min_jours: 2 });
  });

  it("attribue, retient la caution, annule", async () => {
    await locations.lireChoixAttribution("l1");
    expect(api.get).toHaveBeenLastCalledWith("/v1/admin/location/locations/l1/loueurs/", { params: { chauffeurs: 1 } });
    await locations.attribuerLocation("l1", { partenaire: 3 });
    expect(api.post).toHaveBeenLastCalledWith("/v1/admin/location/locations/l1/attribuer/", { partenaire: 3 });
    await locations.retenirCaution("l1", { montant: 5000, motif: "Rayure" });
    expect(api.post).toHaveBeenLastCalledWith("/v1/admin/location/locations/l1/caution/", { montant: 5000, motif: "Rayure" });
    await locations.annulerLocationAdmin("l1", "Panne");
    expect(api.post).toHaveBeenLastCalledWith("/v1/admin/location/locations/l1/annuler/", { motif: "Panne" });
  });
});
