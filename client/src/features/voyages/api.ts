import api from "@/lib/api";
import type { Hebergement, Paginated } from "@/types/api/models";
import type { ApercuInvitation, Voyage, VoyageResume } from "./types";

const VOYAGES = "/v1/voyages";
type ChampsVoyage = Partial<Pick<Voyage, "nom" | "destination" | "date_debut" | "date_fin" | "nb_voyageurs" | "notes">>;

export async function listerVoyages() {
  return (await api.get<{ results: VoyageResume[] }>(`${VOYAGES}/`)).data.results;
}

export async function lireVoyage(id: string) {
  return (await api.get<Voyage>(`${VOYAGES}/${id}/`)).data;
}

export async function creerVoyage(voyage: ChampsVoyage) {
  return (await api.post<Voyage>(`${VOYAGES}/`, voyage)).data;
}

export async function modifierVoyage(id: string, champs: ChampsVoyage) {
  return (await api.patch<Voyage>(`${VOYAGES}/${id}/`, champs)).data;
}

export async function supprimerVoyage(id: string) {
  await api.delete(`${VOYAGES}/${id}/`);
}

export async function proposerLogement(id: string, hebergement: string) {
  return (await api.post<Voyage>(`${VOYAGES}/${id}/propositions/`, { hebergement })).data;
}

export async function retirerProposition(id: string, proposition: number) {
  return (await api.delete<Voyage>(`${VOYAGES}/${id}/propositions/${proposition}/`)).data;
}

export async function voter(id: string, proposition: number) {
  return (await api.post<Voyage>(`${VOYAGES}/${id}/vote/`, { proposition })).data;
}

export async function retirerVote(id: string) {
  return (await api.delete<Voyage>(`${VOYAGES}/${id}/vote/`)).data;
}

export async function retenirProposition(id: string, proposition: number) {
  return (await api.post<Voyage>(`${VOYAGES}/${id}/retenir/`, { proposition })).data;
}

export async function ajouterEtape(id: string, etape: Record<string, unknown>) {
  return (await api.post<Voyage>(`${VOYAGES}/${id}/etapes/`, etape)).data;
}

export async function retirerEtape(id: string, etape: number) {
  await api.delete(`${VOYAGES}/${id}/etapes/${etape}/`);
}

export async function partagerReservation(id: string, reservation: string) {
  return (await api.post<Voyage>(`${VOYAGES}/${id}/reservations/`, { reservation })).data;
}

export async function retirerReservation(id: string, partage: number) {
  await api.delete(`${VOYAGES}/${id}/reservations/${partage}/`);
}

export async function retirerMembre(id: string, membre: string) {
  await api.delete(`${VOYAGES}/${id}/membres/${membre}/`);
}

export async function nouveauLien(id: string) {
  await api.post(`${VOYAGES}/${id}/nouveau-lien/`);
}

export async function lireInvitation(code: string) {
  return (await api.get<ApercuInvitation>(`${VOYAGES}/invitations/${code}/`)).data;
}

export async function rejoindre(code: string) {
  return (await api.post<{ id: string }>(`${VOYAGES}/invitations/${code}/`)).data;
}

/** Listings that can be suggested to the group. */
export async function chercherLogements(params: { q?: string; check_in?: string; check_out?: string; limit: number }) {
  return (await api.get<Paginated<Hebergement>>("/v1/hebergements/", { params })).data.results;
}

