import { beforeEach, describe, expect, it, vi } from "vitest";
import api from "@/lib/api";
import { verifierTexte } from "./api";

vi.mock("@/lib/api", () => ({ default: { post: vi.fn() } }));

describe("correcteur", () => {
  beforeEach(() => vi.clearAllMocks());

  it("envoie le texte et la langue du site", async () => {
    vi.mocked(api.post).mockResolvedValue({ data: { disponible: true, fautes: [] } });
    const signal = new AbortController().signal;
    await expect(verifierTexte("Une mason", "fr", signal)).resolves.toEqual({ disponible: true, fautes: [] });
    expect(api.post).toHaveBeenCalledWith("/v1/correcteur/verifier/", { texte: "Une mason", langue: "fr" }, { signal });
  });
});
