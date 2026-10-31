import { useQuery } from "@tanstack/react-query";
import { useSession } from "next-auth/react";
import { estPagePaiement } from "@/lib/url-sure";
import type { MoyenPaiement } from "@/types/api/paiement";
import { demarrerPaiementLocation, demarrerPaiementReservation, demarrerPaiementTransfert, lireConfig, lireDevis, lireRevenus } from "./api";

/** Public online payment settings (active or not, rates, countries and operators). */
export function useConfigPaiement() {
  return useQuery({
    queryKey: ["paiements", "config"],
    queryFn: lireConfig,
    // Short: a payment method enabled on the server must show without reloading the page
    staleTime: 60 * 1000,
  });
}

/** Amounts of a stay, computed by the API: rates of this host and of this visitor, who may be a loyal customer. */
export function useDevisSejour(hebergementId: string, nuits: number, typeLogement: string | undefined, nbUnites: number) {
  const { status } = useSession();
  return useQuery({
    queryKey: ["hebergement", hebergementId, "devis", nuits, typeLogement, nbUnites, status],
    queryFn: () => lireDevis(hebergementId, { nuits, nb_unites: nbUnites, ...(typeLogement ? { type_logement: typeLogement } : {}) }),
    enabled: nuits > 0 && status !== "loading",
    retry: false,
  });
}

export const CLE_REVENUS = ["paiements", "revenus"];

export function useRevenus() {
  return useQuery({ queryKey: CLE_REVENUS, queryFn: lireRevenus });
}

/** Leaves the site for the provider's payment page. Any other address fails like a refused payment, for the caller to show. */
export function versPagePaiement(url: string) {
  if (!estPagePaiement(url)) throw new Error("Adresse de paiement inattendue");
  window.location.assign(url);
}

/** Creates the FedaPay transaction and sends the browser to the secure payment page. */
export async function allerPayer(reservationId: string, moyen?: MoyenPaiement) {
  versPagePaiement(await demarrerPaiementReservation(reservationId, moyen));
}

/** Payment of an airport transfer: same principle as for a listing. */
export async function payerTransfert(transfertId: string, moyen: MoyenPaiement) {
  versPagePaiement(await demarrerPaiementTransfert(transfertId, moyen));
}

export async function payerLocation(locationId: string, moyen: MoyenPaiement) {
  versPagePaiement(await demarrerPaiementLocation(locationId, moyen));
}

/** Time left before the dates are released, in minutes (rounded up). */
export function minutesRestantes(expireLe: string | null): number | null {
  if (!expireLe) return null;
  return Math.max(0, Math.ceil((new Date(expireLe).getTime() - Date.now()) / 60000));
}

/** Amount in euros charged by PayPal (fixed FCFA/euro parity). */
export function enEuros(montantFcfa: number, fcfaParEuro: number): string {
  return (Math.round((montantFcfa / fcfaParEuro) * 100) / 100).toLocaleString("fr-FR", { style: "currency", currency: "EUR" });
}

/**
 * Mobile Money operators offered, as returned by the API: at launch Moov Money (Flooz) and Mixx by Yas
 * (T-Money); the others are added when the switch of the not-yet-open methods is on.
 */
export function useOperateursMobileMoney(): string {
  const { data } = useConfigPaiement();
  const noms = data?.pays.flatMap((p) => p.operateurs.map((o) => o.nom)) ?? ["Moov Money (Flooz)", "Mixx by Yas (T-Money)"];
  return Array.from(new Set(noms)).join(", ");
}
