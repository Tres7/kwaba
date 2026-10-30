import { beforeEach, describe, expect, it, vi } from "vitest";
import api from "@/lib/api";
import { ajouterFavori, listerFavoris, retirerFavori } from "./api";

vi.mock("@/lib/api", () => ({ default: { get: vi.fn(), post: vi.fn(), delete: vi.fn() } }));

describe("favoris", () => {
  beforeEach(() => vi.clearAllMocks());

  it("liste les résultats de la page", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: { results: [{ id: "f1" }] } });
    await expect(listerFavoris()).resolves.toEqual([{ id: "f1" }]);
    expect(api.get).toHaveBeenCalledWith("/v1/favoris/");
  });

  it("ajoute par l'identifiant de l'annonce", async () => {
    await ajouterFavori("h1");
    expect(api.post).toHaveBeenCalledWith("/v1/favoris/", { hebergement: "h1" });
  });

  it("retire par l'identifiant de l'annonce", async () => {
    await retirerFavori("h1");
    expect(api.delete).toHaveBeenCalledWith("/v1/favoris/h1/");
  });
});
