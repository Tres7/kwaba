import { beforeEach, describe, expect, it, vi } from "vitest";
import api from "@/lib/api";
import { telechargerPdf } from "@/lib/documents";
import * as contrats from "./api";
import type { SignatureContrat } from "./types";

vi.mock("@/lib/api", () => ({ default: { get: vi.fn(), post: vi.fn(), put: vi.fn() } }));
vi.mock("@/lib/documents", () => ({ telechargerPdf: vi.fn() }));

const SIGNATURE = { nom: "Kossi" } as unknown as SignatureContrat;

describe("contrats", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    for (const m of [api.get, api.post, api.put]) vi.mocked(m).mockResolvedValue({ data: { id: "c1" } });
  });

  it("lit et signe par le lien personnel", async () => {
    await contrats.lireContrat("jeton");
    expect(api.get).toHaveBeenLastCalledWith("/v1/contrats/signature/jeton/");
    await contrats.signerContrat("jeton", SIGNATURE);
    expect(api.post).toHaveBeenLastCalledWith("/v1/contrats/signature/jeton/signer/", SIGNATURE);
    contrats.telechargerContrat("jeton", "C-1");
    expect(telechargerPdf).toHaveBeenLastCalledWith("/v1/contrats/signature/jeton/pdf/", "contrat-C-1.pdf");
  });

  it("le contrat de l'hôte connecté porte la version lue", async () => {
    await contrats.lireContratHote();
    expect(api.get).toHaveBeenLastCalledWith("/v1/contrats/hote/");
    await contrats.signerContratHote({ ...SIGNATURE, version: 3 });
    expect(api.post).toHaveBeenLastCalledWith("/v1/contrats/hote/signer/", { nom: "Kossi", version: 3 });
    contrats.telechargerContratHote();
    expect(telechargerPdf).toHaveBeenLastCalledWith("/v1/contrats/hote/pdf/", "contrat-hote.pdf");
  });

  it("accepte la pré-inscription avec la version et la langue lues", async () => {
    await contrats.lirePreinscription();
    expect(api.get).toHaveBeenLastCalledWith("/v1/contrats/preinscription/");
    await contrats.accepterPreinscription("v2" as never, "fr" as never);
    expect(api.post).toHaveBeenLastCalledWith("/v1/contrats/preinscription/", { accepte: true, version: "v2", langue: "fr" });
  });

  it("gère les contrats du back-office", async () => {
    await contrats.listerParties("hote", "Kossi");
    expect(api.get).toHaveBeenLastCalledWith("/v1/admin/contrats/parties/", { params: { type: "hote", q: "Kossi" } });
    await contrats.creerContrat("hote", "p1");
    expect(api.post).toHaveBeenLastCalledWith("/v1/admin/contrats/", { type: "hote", partie_id: "p1" });
    await contrats.agirSurContrat("c1", "renvoyer");
    expect(api.post).toHaveBeenLastCalledWith("/v1/admin/contrats/c1/renvoyer/", {});
    await contrats.agirSurContrat("c1", "annuler", "Erreur");
    expect(api.post).toHaveBeenLastCalledWith("/v1/admin/contrats/c1/annuler/", { motif: "Erreur" });
    contrats.telechargerContratAdmin({ id: "c1", reference: "C-1" });
    expect(telechargerPdf).toHaveBeenLastCalledWith("/v1/admin/contrats/c1/pdf/", "contrat-C-1.pdf");
  });

  it("lit et enregistre les modèles", async () => {
    await contrats.listerModeles();
    expect(api.get).toHaveBeenLastCalledWith("/v1/admin/contrats/modeles/");
    await contrats.enregistrerModele("hote", { titre: "T", corps: "C" });
    expect(api.put).toHaveBeenLastCalledWith("/v1/admin/contrats/modeles/hote/", { titre: "T", corps: "C" });
  });
});
