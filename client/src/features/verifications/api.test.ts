import { beforeEach, describe, expect, it, vi } from "vitest";
import api from "@/lib/api";
import * as verifications from "./api";

vi.mock("@/lib/api", () => ({ default: { get: vi.fn(), post: vi.fn() } }));

const MULTIPART = { headers: { "Content-Type": "multipart/form-data" } };

describe("verifications", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.get).mockResolvedValue({ data: { ok: true } });
  });

  it("lit le tableau, les missions et les compteurs", async () => {
    await verifications.lireTableauAgent();
    expect(api.get).toHaveBeenLastCalledWith("/v1/agent/tableau/");
    await verifications.listerMissions({ vue: "a_faire", q: "Lomé" });
    expect(api.get).toHaveBeenLastCalledWith("/v1/agent/missions/", { params: { vue: "a_faire", q: "Lomé" } });
    await verifications.lireMission("logement", "c1");
    expect(api.get).toHaveBeenLastCalledWith("/v1/agent/missions/logement/c1/");
    await verifications.lireCompteurs();
    expect(api.get).toHaveBeenLastCalledWith("/v1/verifications/compteurs/");
  });

  it.each(["prendre", "liberer"] as const)("%s une mission", async (action) => {
    await verifications.agirSurMission("piece", "c1", action);
    expect(api.post).toHaveBeenCalledWith(`/v1/agent/missions/piece/c1/${action}/`);
  });

  it("enregistre les décisions", async () => {
    const corps = new FormData();
    await verifications.deciderVisite("l1", corps);
    expect(api.post).toHaveBeenLastCalledWith("/v1/verifications/visites/l1/decision/", corps, MULTIPART);
    await verifications.deciderPiece("h1", { decision: "verifiee", motif: "" });
    expect(api.post).toHaveBeenLastCalledWith("/v1/verifications/identites/h1/decision/", { decision: "verifiee", motif: "" });
  });

  it("lit la pièce d'un hôte en binaire, jamais par une adresse publique", async () => {
    await verifications.lireFichierPiece("h1");
    expect(api.get).toHaveBeenCalledWith("/v1/verifications/identite/h1/fichier/", { responseType: "blob" });
  });

  it("lit et envoie sa propre pièce", async () => {
    await verifications.lireMaPiece();
    expect(api.get).toHaveBeenLastCalledWith("/v1/verifications/identite/");
    const corps = new FormData();
    await verifications.envoyerMaPiece(corps);
    expect(api.post).toHaveBeenLastCalledWith("/v1/verifications/identite/", corps, MULTIPART);
  });
});
