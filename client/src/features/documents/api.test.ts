import { beforeEach, describe, expect, it, vi } from "vitest";
import api from "@/lib/api";
import { telechargerPdf } from "@/lib/documents";
import { emettreFacture, enregistrerSociete, factureDe, lireSignature, lireSociete, telechargerDocument, telechargerFacture } from "./api";

vi.mock("@/lib/api", () => ({ default: { get: vi.fn(), post: vi.fn(), put: vi.fn() } }));
vi.mock("@/lib/documents", () => ({ telechargerPdf: vi.fn() }));

describe("documents", () => {
  beforeEach(() => vi.clearAllMocks());

  it("télécharge un document avec un nom par défaut", () => {
    telechargerDocument("reservation", "r1", "bon");
    expect(telechargerPdf).toHaveBeenCalledWith("/v1/documents/reservation/r1/bon/", "bon-r1.pdf");
  });

  it("télécharge une facture", () => {
    telechargerFacture({ id: "f1", numero: "F-1" });
    expect(telechargerPdf).toHaveBeenCalledWith("/v1/admin/documents/factures/f1/pdf/", "facture-F-1.pdf");
  });

  it("émet une facture", async () => {
    vi.mocked(api.post).mockResolvedValue({ data: { id: "f1" } });
    await expect(emettreFacture({ lignes: [] })).resolves.toEqual({ id: "f1" });
    expect(api.post).toHaveBeenCalledWith("/v1/admin/documents/factures/", { lignes: [] });
  });

  it("émet puis télécharge la facture d'un séjour", async () => {
    vi.mocked(api.post).mockResolvedValue({ data: { id: "f1", numero: "F-1" } });
    await factureDe("reservation", "r1");
    expect(api.post).toHaveBeenCalledWith("/v1/admin/documents/factures/", { objet_type: "reservation", objet_id: "r1" });
    expect(telechargerPdf).toHaveBeenCalledWith("/v1/admin/documents/factures/f1/pdf/", "facture-F-1.pdf");
  });

  it("lit et enregistre les informations de la société", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: {} });
    vi.mocked(api.put).mockResolvedValue({ data: {} });
    await lireSociete();
    expect(api.get).toHaveBeenCalledWith("/v1/admin/documents/societe/");
    const corps = new FormData();
    await enregistrerSociete(corps);
    expect(api.put).toHaveBeenCalledWith("/v1/admin/documents/societe/", corps, { headers: { "Content-Type": "multipart/form-data" } });
  });

  it("lit la signature en binaire", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: new Blob() });
    await lireSignature();
    expect(api.get).toHaveBeenCalledWith("/v1/admin/documents/societe/signature/", { responseType: "blob" });
  });
});
