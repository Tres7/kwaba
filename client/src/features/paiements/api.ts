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

// --- Back-office: rates (AN-B1) and finances of a period (AN-B2)

export interface TarifsAdmin {
  /** In %: 6 means 6 % */
  taux: Record<"frais_voyageur" | "frais_reduits" | "commission_particulier" | "commission_hotel" | "commission_fondateur"
    | "commission_transfert", number>;
  /** FCFA per stay, by listing type */
  frais_menage: Record<string, number>;
  mis_a_jour_le: string | null;
}

export async function lireTarifsAdmin() {
  return (await api.get<TarifsAdmin>("/v1/admin/paiements/tarifs/")).data;
}

export async function modifierTarifsAdmin(tarifs: Pick<TarifsAdmin, "taux" | "frais_menage">) {
  return (await api.put<TarifsAdmin>("/v1/admin/paiements/tarifs/", tarifs)).data;
}

export interface VersementFinances {
  categorie: string; beneficiaire: string; objet: string; montant: number; commission: number; statut: string;
  date_prevue: string; envoye_le: string | null;
}

export interface Finances {
  debut: string;
  fin: string;
  totaux: { encaisse: number; nb_paiements: number; rembourse: number; rembourse_en_attente: number; verse: number;
    du_partenaires: number; revenu_kwaba: number };
  par_produit: Record<string, number>;
  par_prestataire: Record<string, number>;
  jours: { date: string; nb_paiements: number; encaisse: number; rembourse: number; verse: number; solde: number }[];
  versements: VersementFinances[];
}

export const URL_EXPORT_FINANCES = "/v1/admin/paiements/finances/";

export async function lireFinances(debut: string, fin: string) {
  return (await api.get<Finances>(URL_EXPORT_FINANCES, { params: { debut, fin } })).data;
}
