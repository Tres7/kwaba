import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { estPagePaiement } from "@/lib/url-sure";
import type { ConfigPaiement, MoyenPaiement } from "@/types/api/paiement";

/** Public online payment settings (active or not, rates, countries and operators). */
export function useConfigPaiement() {
  return useQuery({
    queryKey: ["paiements", "config"],
    queryFn: async () => (await api.get<ConfigPaiement>("/v1/paiements/config/")).data,
    // Short: a payment method enabled on the server must show without reloading the page
    staleTime: 60 * 1000,
  });
}

/** Leaves the site for the provider's payment page. Any other address fails like a refused payment, for the caller to show. */
export function versPagePaiement(url: string) {
  if (!estPagePaiement(url)) throw new Error("Adresse de paiement inattendue");
  window.location.assign(url);
}

/** Creates the FedaPay transaction and sends the browser to the secure payment page. */
export async function allerPayer(reservationId: string, moyen?: MoyenPaiement) {
  const res = await api.post<{ url: string }>(`/v1/paiements/reservations/${reservationId}/payer/`, moyen ? { moyen } : {});
  versPagePaiement(res.data.url);
}

/** Payment of an airport transfer: same principle as for a listing. */
export async function payerTransfert(transfertId: string, moyen: MoyenPaiement) {
  const res = await api.post<{ url: string }>(`/v1/transferts/${transfertId}/payer/`, { moyen });
  versPagePaiement(res.data.url);
}

export async function payerLocation(locationId: string, moyen: MoyenPaiement) {
  const res = await api.post<{ url: string }>(`/v1/locations/${locationId}/payer/`, { moyen });
  versPagePaiement(res.data.url);
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
