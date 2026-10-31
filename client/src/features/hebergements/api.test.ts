import { beforeEach, describe, expect, it, vi } from "vitest";
import api from "@/lib/api";
import * as h from "./api";

vi.mock("@/lib/api", () => ({ default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn() } }));

describe("hebergements", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    for (const m of [api.get, api.post, api.put, api.patch]) vi.mocked(m).mockResolvedValue({ data: { id: "h1", results: [{ id: "h1" }], periodes: [], count: 0, prelancement: true } });
  });

  it("cherche, lit et liste", async () => {
    await h.chercherHebergements({ city: "Lomé", limit: 8 });
    expect(api.get).toHaveBeenLastCalledWith("/v1/hebergements/", { params: { city: "Lomé", limit: 8 } });
    await h.lireHebergement("h1");
    expect(api.get).toHaveBeenLastCalledWith("/v1/hebergements/h1/");
    await expect(h.listerMesHebergements()).resolves.toEqual([{ id: "h1" }]);
    expect(api.get).toHaveBeenLastCalledWith("/v1/hebergements/mine/");
    await h.listerVilles();
    expect(api.get).toHaveBeenLastCalledWith("/v1/hebergements/villes/");
    await h.suggererDestinations("Lo");
    expect(api.get).toHaveBeenLastCalledWith("/v1/hebergements/suggestions/", { params: { q: "Lo" } });
  });

  it("crée, modifie et supprime une annonce", async () => {
    await h.creerHebergement({ name: "Villa" });
    expect(api.post).toHaveBeenLastCalledWith("/v1/hebergements/", { name: "Villa" });
    await h.modifierHebergement("h1", { is_available: false });
    expect(api.patch).toHaveBeenLastCalledWith("/v1/hebergements/h1/", { is_available: false });
    await h.supprimerHebergement("h1");
    expect(api.delete).toHaveBeenLastCalledWith("/v1/hebergements/h1/");
  });

  it("lists, creates, updates and deletes a draft", async () => {
    await expect(h.listerBrouillons()).resolves.toEqual([{ id: "h1" }]);
    expect(api.get).toHaveBeenLastCalledWith("/v1/hebergements/brouillons/");
    await h.creerBrouillon({ name: "Villa" });
    expect(api.post).toHaveBeenLastCalledWith("/v1/hebergements/brouillons/", { donnees: { name: "Villa" } });
    await h.modifierBrouillon("b1", { name: "Villa", city: "Lomé" });
    expect(api.put).toHaveBeenLastCalledWith("/v1/hebergements/brouillons/b1/", { donnees: { name: "Villa", city: "Lomé" } });
    await h.supprimerBrouillon("b1");
    expect(api.delete).toHaveBeenLastCalledWith("/v1/hebergements/brouillons/b1/");
  });

  it("lit les disponibilités et ferme ou rouvre des dates", async () => {
    await h.lireDisponibilites("h1", { debut: "2026-12-01", fin: "2026-12-31" });
    expect(api.get).toHaveBeenLastCalledWith("/v1/hebergements/h1/disponibilites/", { params: { debut: "2026-12-01", fin: "2026-12-31" } });
    await h.fermerDates("h1", { debut: "2026-12-01", fin: "2026-12-02", motif: "Travaux" });
    expect(api.post).toHaveBeenLastCalledWith("/v1/hebergements/h1/blocages/", { debut: "2026-12-01", fin: "2026-12-02", motif: "Travaux" });
    await h.rouvrirDates("b1");
    expect(api.delete).toHaveBeenLastCalledWith("/v1/hebergements/blocages/b1/");
  });

  it("gère les types de logement", async () => {
    await h.listerTypes("h1");
    expect(api.get).toHaveBeenLastCalledWith("/v1/hebergements/h1/types/");
    await h.creerType("h1", { nom: "Suite" });
    expect(api.post).toHaveBeenLastCalledWith("/v1/hebergements/h1/types/", { nom: "Suite" });
    await h.modifierType("t1", { actif: false });
    expect(api.patch).toHaveBeenLastCalledWith("/v1/hebergements/types/t1/", { actif: false });
    await h.supprimerType("t1");
    expect(api.delete).toHaveBeenLastCalledWith("/v1/hebergements/types/t1/");
  });

  it("envoie une photo et signale sa progression", async () => {
    const corps = new FormData();
    const progression = vi.fn();
    await h.envoyerPhoto(corps, progression);
    const [chemin, envoye, options] = vi.mocked(api.post).mock.calls[0];
    expect(chemin).toBe("/v1/hebergements/photos/");
    expect(envoye).toBe(corps);
    expect(options?.headers).toEqual({ "Content-Type": "multipart/form-data" });
    options?.onUploadProgress?.({ loaded: 50, total: 200 } as never);
    expect(progression).toHaveBeenCalledWith(25);
    await h.supprimerPhoto("p1");
    expect(api.delete).toHaveBeenLastCalledWith("/v1/hebergements/photos/p1/");
  });

  it("crée une alerte et répond depuis un lien", async () => {
    await h.creerAlerte("h1", { debut: "2026-12-01" });
    expect(api.post).toHaveBeenLastCalledWith("/v1/hebergements/h1/alertes/", { debut: "2026-12-01" });
    await h.repondreAlerte("desabonner", "jeton");
    expect(api.post).toHaveBeenLastCalledWith("/v1/hebergements/alertes/desabonner/", { jeton: "jeton" });
  });

  it("gère l'ouverture", async () => {
    await expect(h.lirePrelancement()).resolves.toBe(true);
    expect(api.get).toHaveBeenLastCalledWith("/v1/hebergements/lancement/");
    await expect(h.compterLogements()).resolves.toBe(0);
    expect(api.get).toHaveBeenLastCalledWith("/v1/hebergements/", { params: { limit: 1 } });
    await h.sInscrireOuverture("a@b.c", "fr");
    expect(api.post).toHaveBeenLastCalledWith("/v1/hebergements/lancement/", { email: "a@b.c", langue: "fr" });
  });

  it("gère les annonces du back-office", async () => {
    await h.restaurerAnnonce("h1");
    expect(api.post).toHaveBeenLastCalledWith("/v1/admin/hebergements/h1/restaurer/");
    await h.modifierAnnonceAdmin("h1", { est_verifie: true });
    expect(api.patch).toHaveBeenLastCalledWith("/v1/admin/hebergements/h1/", { est_verifie: true });
    await h.supprimerAnnonceAdmin("h1", "Doublon");
    expect(api.delete).toHaveBeenLastCalledWith("/v1/admin/hebergements/h1/", { params: { motif: "Doublon" } });
    await h.lireLancementAdmin();
    expect(api.get).toHaveBeenLastCalledWith("/v1/admin/lancement/");
    await h.annoncerOuverture();
    expect(api.post).toHaveBeenLastCalledWith("/v1/admin/lancement/");
  });
});
