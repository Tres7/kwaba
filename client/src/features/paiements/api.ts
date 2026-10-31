import api from "@/lib/api";
import type { ConfigPaiement, DevisSejour, MoyenPaiement, ProfilVersement, Revenus, StatutPaiementReservation } from "@/types/api/paiement";

const PAIEMENTS = "/v1/paiements";

export async function lireConfig() {
  return (await api.get<ConfigPaiement>(`${PAIEMENTS}/config/`)).data;
}

export async function lireDevis(hebergementId: string, params: Record<string, string | number>) {
  return (await api.get<DevisSejour>(`/v1/hebergements/${hebergementId}/devis/`, { params })).data;
}

/** Creates the FedaPay transaction: the answer gives the secure payment page. */
export async function demarrerPaiementReservation(reservationId: string, moyen?: MoyenPaiement) {
  return (await api.post<{ url: string }>(`${PAIEMENTS}/reservations/${reservationId}/payer/`, moyen ? { moyen } : {})).data.url;
}

export async function demarrerPaiementTransfert(transfertId: string, moyen: MoyenPaiement) {
  return (await api.post<{ url: string }>(`/v1/transferts/${transfertId}/payer/`, { moyen })).data.url;
}

export async function demarrerPaiementLocation(locationId: string, moyen: MoyenPaiement) {
  return (await api.post<{ url: string }>(`/v1/locations/${locationId}/payer/`, { moyen })).data.url;
}

export async function lireStatutReservation(reservationId: string) {
  return (await api.get<StatutPaiementReservation>(`${PAIEMENTS}/reservations/${reservationId}/statut/`)).data;
}

export const adresseCompteReservation = (reservationId: string) => `${PAIEMENTS}/reservations/${reservationId}/compte-remboursement/`;

/** `adresse`: the refund account of a stay, a transfer or a rental. */
export async function enregistrerCompteRemboursement(adresse: string, compte: { pays: string; operateur: string; numero: string }) {
  await api.put(adresse, compte);
}

export async function lireRevenus() {
  return (await api.get<Revenus>(`${PAIEMENTS}/revenus/`)).data;
}

export async function lireProfilVersement() {
  return (await api.get<ProfilVersement | null>(`${PAIEMENTS}/profil-versement/`)).data;
}

export async function enregistrerProfilVersement(profil: ProfilVersement) {
  return (await api.put<ProfilVersement>(`${PAIEMENTS}/profil-versement/`, profil)).data;
}
