import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import api from "@/lib/api";
import { creerConversation, creerVoyageDeGroupe, lireMessages, lireStatut, listerConversations, posterMessage, supprimerConversation } from "./api";
import type { CarteTogether } from "./types";

vi.mock("@/lib/api", () => ({ default: { get: vi.fn(), post: vi.fn(), delete: vi.fn() } }));

describe("concierge", () => {
  beforeEach(() => vi.clearAllMocks());
  afterEach(() => vi.unstubAllGlobals());

  it("lit le statut, les conversations et les messages", async () => {
    vi.mocked(api.get).mockResolvedValueOnce({ data: { actif: true } });
    await expect(lireStatut()).resolves.toEqual({ actif: true });
    expect(api.get).toHaveBeenLastCalledWith("/v1/concierge/statut/");

    vi.mocked(api.get).mockResolvedValueOnce({ data: { results: [{ id: "c1" }] } });
    await expect(listerConversations()).resolves.toEqual([{ id: "c1" }]);
    expect(api.get).toHaveBeenLastCalledWith("/v1/concierge/conversations/");

    vi.mocked(api.get).mockResolvedValueOnce({ data: { messages: [{ role: "user" }] } });
    await expect(lireMessages("c1")).resolves.toEqual([{ role: "user" }]);
    expect(api.get).toHaveBeenLastCalledWith("/v1/concierge/conversations/c1/");
  });

  it("crée et supprime une conversation", async () => {
    vi.mocked(api.post).mockResolvedValue({ data: { id: "c1" } });
    await expect(creerConversation()).resolves.toBe("c1");
    expect(api.post).toHaveBeenCalledWith("/v1/concierge/conversations/");
    await supprimerConversation("c1");
    expect(api.delete).toHaveBeenCalledWith("/v1/concierge/conversations/c1/");
  });

  it("envoie le message au proxy, dans la langue de la page", async () => {
    const reponse = { ok: true };
    const envoi = vi.fn().mockResolvedValue(reponse);
    vi.stubGlobal("fetch", envoi);
    await expect(posterMessage("c1", "Bonjour", "en", "Erreur")).resolves.toBe(reponse);
    expect(envoi).toHaveBeenCalledWith("/api/proxy/v1/concierge/conversations/c1/messages", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept-Language": "en" },
      body: JSON.stringify({ texte: "Bonjour" }),
    });
  });

  it.each([
    [{ detail: "Limite atteinte" }, "Limite atteinte"],
    [{ texte: ["Trop long"] }, "Trop long"],
    [{}, "Erreur"],
  ])("un refus renvoie le message de l'API, sinon le message prévu (%j)", async (corps, attendu) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, json: async () => corps }));
    await expect(posterMessage("c1", "Bonjour", "fr", "Erreur")).rejects.toThrow(attendu);
  });

  it("crée le voyage même si un logement est refusé", async () => {
    vi.mocked(api.post).mockResolvedValueOnce({ data: { id: "v1" } }).mockRejectedValueOnce(new Error("refusé")).mockResolvedValueOnce({ data: {} });
    const carte = { nom: "Lomé", destination: "Lomé", arrivee: "2026-12-01", depart: "2026-12-05", voyageurs: 4, logements: [{ id: "h1" }, { id: "h2" }] } as CarteTogether;
    await expect(creerVoyageDeGroupe(carte)).resolves.toBe("v1");
    expect(api.post).toHaveBeenCalledWith("/v1/voyages/", { nom: "Lomé", destination: "Lomé", date_debut: "2026-12-01", date_fin: "2026-12-05", nb_voyageurs: 4 });
    expect(api.post).toHaveBeenCalledWith("/v1/voyages/v1/propositions/", { hebergement: "h2" });
  });
});
