import api from "@/lib/api";
import type { MoyenPaiement } from "@/types/api/paiement";
import type { ApercuTiers, DemandeTiers, StatutTiers } from "./types";

const PAIEMENTS = "/v1/paiements";
const demande = (reservationId: string) => `${PAIEMENTS}/reservations/${encodeURIComponent(reservationId)}/demande-tiers/`;

// --- The traveller ------------------------------------------------------------------------------------------------

export async function lireDemandeTiers(reservationId: string) {
  return (await api.get<DemandeTiers>(demande(reservationId))).data;
}

/** New secret link (the previous one stops working): the only time the API gives it. */
export async function creerLienTiers(reservationId: string) {
  return (await api.post<DemandeTiers>(demande(reservationId))).data;
}

export async function desactiverLienTiers(reservationId: string) {
  await api.delete(demande(reservationId));
}

// --- The payer, by the secret link --------------------------------------------------------------------------------

export async function lireApercuTiers(jeton: string) {
  return (await api.get<ApercuTiers>(`${PAIEMENTS}/tiers/${encodeURIComponent(jeton)}/`)).data;
}

export async function demarrerPaiementTiers(jeton: string, moyen: MoyenPaiement) {
  return (await api.post<{ url: string }>(`${PAIEMENTS}/tiers/${encodeURIComponent(jeton)}/`, { moyen })).data.url;
}

export async function lireStatutTiers(demandeId: string) {
  return (await api.get<StatutTiers>(`${PAIEMENTS}/tiers/demandes/${encodeURIComponent(demandeId)}/statut/`)).data;
}
