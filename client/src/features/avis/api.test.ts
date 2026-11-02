import { beforeEach, describe, expect, it, vi } from "vitest";
import api from "@/lib/api";
import { listerAvis, listerSejoursAEvaluer, publierAvis, repondreAvis, supprimerAvisAdmin } from "./api";

vi.mock("@/lib/api", () => ({ default: { get: vi.fn(), post: vi.fn(), delete: vi.fn() } }));

describe("avis", () => {
  beforeEach(() => vi.clearAllMocks());

  it("lit les avis d'une annonce, page par page", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: { results: [], count: 0 } });
    await listerAvis("h1", { limit: 6, offset: 12 });
    expect(api.get).toHaveBeenCalledWith("/v1/avis/", { params: { hebergement: "h1", limit: 6, offset: 12 } });
  });

  it("répond à un avis et renvoie l'avis à jour", async () => {
    vi.mocked(api.post).mockResolvedValue({ data: { id: "a1", reponse_hote: "Merci" } });
    await expect(repondreAvis("a1", "Merci")).resolves.toMatchObject({ reponse_hote: "Merci" });
    expect(api.post).toHaveBeenCalledWith("/v1/avis/a1/reponse/", { reponse: "Merci" });
  });

  it("liste les séjours à évaluer", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: { results: [{ reservation_id: "r1" }] } });
    await expect(listerSejoursAEvaluer()).resolves.toEqual([{ reservation_id: "r1" }]);
    expect(api.get).toHaveBeenCalledWith("/v1/avis/a-laisser/");
  });

  it("publie un avis avec ses critères", async () => {
    await publierAvis({ reservation: "r1", note: 5, proprete: 4, commentaire: "Très bien" });
    expect(api.post).toHaveBeenCalledWith("/v1/avis/", { reservation: "r1", note: 5, proprete: 4, commentaire: "Très bien" });
  });

  it("supprime un avis côté back-office avec son motif", async () => {
    await supprimerAvisAdmin("a1", "Insultes");
    expect(api.delete).toHaveBeenCalledWith("/v1/admin/avis/a1/", { params: { motif: "Insultes" } });
  });
});
