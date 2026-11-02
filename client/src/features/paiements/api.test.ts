import { beforeEach, describe, expect, it, vi } from "vitest";
import api from "@/lib/api";
import * as paiements from "./api";

vi.mock("@/lib/api", () => ({ default: { get: vi.fn(), post: vi.fn(), put: vi.fn() } }));

describe("paiements", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    for (const m of [api.get, api.post, api.put]) vi.mocked(m).mockResolvedValue({ data: { url: "https://pay" } });
  });

  it("lit la configuration et le devis calculé par l'API", async () => {
    await paiements.lireConfig();
    expect(api.get).toHaveBeenLastCalledWith("/v1/paiements/config/");
    await paiements.lireDevis("h1", { nuits: 3, nb_unites: 1 });
    expect(api.get).toHaveBeenLastCalledWith("/v1/hebergements/h1/devis/", { params: { nuits: 3, nb_unites: 1 } });
  });

  it("démarre le paiement d'une réservation, avec ou sans moyen choisi", async () => {
    await expect(paiements.demarrerPaiementReservation("r1", "carte" as never)).resolves.toBe("https://pay");
    expect(api.post).toHaveBeenLastCalledWith("/v1/paiements/reservations/r1/payer/", { moyen: "carte" });
    await paiements.demarrerPaiementReservation("r1");
    expect(api.post).toHaveBeenLastCalledWith("/v1/paiements/reservations/r1/payer/", {});
  });

  it("démarre le paiement d'un transfert et d'une location", async () => {
    await paiements.demarrerPaiementTransfert("t1", "carte" as never);
    expect(api.post).toHaveBeenLastCalledWith("/v1/transferts/t1/payer/", { moyen: "carte" });
    await paiements.demarrerPaiementLocation("l1", "carte" as never);
    expect(api.post).toHaveBeenLastCalledWith("/v1/locations/l1/payer/", { moyen: "carte" });
  });

  it("lit le statut d'un paiement", async () => {
    await paiements.lireStatutReservation("r1");
    expect(api.get).toHaveBeenLastCalledWith("/v1/paiements/reservations/r1/statut/");
  });

  it("enregistre le compte de remboursement à l'adresse donnée", async () => {
    const compte = { pays: "TG", operateur: "moov", numero: "90000000" };
    await paiements.enregistrerCompteRemboursement(paiements.adresseCompteReservation("r1"), compte);
    expect(api.put).toHaveBeenCalledWith("/v1/paiements/reservations/r1/compte-remboursement/", compte);
  });

  it("lit les revenus et le profil de versement", async () => {
    await paiements.lireRevenus();
    expect(api.get).toHaveBeenLastCalledWith("/v1/paiements/revenus/");
    await paiements.lireProfilVersement();
    expect(api.get).toHaveBeenLastCalledWith("/v1/paiements/profil-versement/");
    const profil = { pays: "TG" as const, operateur: "moov", numero: "90", titulaire: "K" };
    await paiements.enregistrerProfilVersement(profil);
    expect(api.put).toHaveBeenLastCalledWith("/v1/paiements/profil-versement/", profil);
  });
});
