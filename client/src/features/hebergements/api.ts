import api from "@/lib/api";
import type { City, Hebergement, Paginated, Reservation, TypeLogement } from "@/types/api/models";
import type { BrouillonAnnonce, DonneesAnnonce } from "./brouillons";
import type { Suggestions } from "./ChampDestination";
import type { PeriodeIndispo } from "./disponibilites";

const HEBERGEMENTS = "/v1/hebergements";
const ADMIN = "/v1/admin/hebergements";

export async function chercherHebergements(params: Record<string, string | number>) {
  return (await api.get<Paginated<Hebergement>>(`${HEBERGEMENTS}/`, { params })).data;
}

export async function lireHebergement(id: string) {
  return (await api.get<Hebergement>(`${HEBERGEMENTS}/${id}/`)).data;
}

export async function listerMesHebergements() {
  return (await api.get<Paginated<Hebergement>>(`${HEBERGEMENTS}/mine/`)).data.results;
}

export async function creerHebergement(annonce: Record<string, unknown>) {
  return (await api.post<Hebergement>(`${HEBERGEMENTS}/`, annonce)).data;
}

export async function modifierHebergement(id: string, champs: Record<string, unknown>) {
  return (await api.patch<Hebergement>(`${HEBERGEMENTS}/${id}/`, champs)).data;
}

export async function supprimerHebergement(id: string) {
  await api.delete(`${HEBERGEMENTS}/${id}/`);
}

export async function listerBrouillons() {
  return (await api.get<{ results: BrouillonAnnonce[] }>(`${HEBERGEMENTS}/brouillons/`)).data.results;
}

export async function creerBrouillon(donnees: DonneesAnnonce) {
  return (await api.post<BrouillonAnnonce>(`${HEBERGEMENTS}/brouillons/`, { donnees })).data;
}

export async function modifierBrouillon(id: string, donnees: DonneesAnnonce) {
  return (await api.put<BrouillonAnnonce>(`${HEBERGEMENTS}/brouillons/${id}/`, { donnees })).data;
}

export async function supprimerBrouillon(id: string) {
  await api.delete(`${HEBERGEMENTS}/brouillons/${id}/`);
}

export async function listerVilles() {
  return (await api.get<{ results: City[] }>(`${HEBERGEMENTS}/villes/`)).data.results;
}

export async function suggererDestinations(q: string) {
  return (await api.get<Suggestions>(`${HEBERGEMENTS}/suggestions/`, { params: { q } })).data;
}

export async function lireDisponibilites(id: string, params: Record<string, string>) {
  return (await api.get<{ periodes: PeriodeIndispo[] }>(`${HEBERGEMENTS}/${id}/disponibilites/`, { params })).data.periodes;
}

export async function fermerDates(id: string, blocage: Record<string, unknown>) {
  await api.post(`${HEBERGEMENTS}/${id}/blocages/`, blocage);
}

export async function rouvrirDates(blocageId: string) {
  await api.delete(`${HEBERGEMENTS}/blocages/${blocageId}/`);
}

export async function listerTypes(id: string) {
  return (await api.get<Paginated<TypeLogement>>(`${HEBERGEMENTS}/${id}/types/`)).data.results;
}

export async function creerType(id: string, type: Record<string, unknown>) {
  await api.post(`${HEBERGEMENTS}/${id}/types/`, type);
}

export async function modifierType(typeId: string, champs: Record<string, unknown>) {
  await api.patch(`${HEBERGEMENTS}/types/${typeId}/`, champs);
}

export async function supprimerType(typeId: string) {
  await api.delete(`${HEBERGEMENTS}/types/${typeId}/`);
}

export async function envoyerPhoto(corps: FormData, progression: (pourcent: number) => void) {
  return (await api.post<{ id: string; url: string }>(`${HEBERGEMENTS}/photos/`, corps, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress: (e) => {
      if (e.total) progression(Math.round((e.loaded / e.total) * 100));
    },
  })).data;
}

export async function supprimerPhoto(id: string) {
  await api.delete(`${HEBERGEMENTS}/photos/${id}/`);
}

export async function creerAlerte<T>(hebergementId: string, alerte: Record<string, unknown>) {
  return (await api.post<T>(`${HEBERGEMENTS}/${hebergementId}/alertes/`, alerte)).data;
}

export async function repondreAlerte<T>(action: string, jeton: string) {
  return (await api.post<T>(`${HEBERGEMENTS}/alertes/${action}/`, { jeton })).data;
}

export async function lirePrelancement() {
  return (await api.get<{ prelancement: boolean }>(`${HEBERGEMENTS}/lancement/`)).data.prelancement;
}

export async function compterLogements() {
  return (await api.get<{ count: number }>(`${HEBERGEMENTS}/`, { params: { limit: 1 } })).data.count;
}

export async function sInscrireOuverture(email: string, langue: string) {
  await api.post(`${HEBERGEMENTS}/lancement/`, { email, langue });
}

export async function listerReservationsHote() {
  return (await api.get<Paginated<Reservation>>("/v1/reservations/", { params: { as: "host" } })).data.results;
}

export function restaurerAnnonce(id: string) {
  return api.post(`${ADMIN}/${id}/restaurer/`);
}

export function modifierAnnonceAdmin(id: string, champs: Record<string, unknown>) {
  return api.patch(`${ADMIN}/${id}/`, champs);
}

export function supprimerAnnonceAdmin(id: string, motif: string) {
  return api.delete(`${ADMIN}/${id}/`, { params: { motif } });
}

export async function lireLancementAdmin<T>() {
  return (await api.get<T>("/v1/admin/lancement/")).data;
}

export async function annoncerOuverture() {
  return (await api.post<{ envoyes: number }>("/v1/admin/lancement/")).data;
}
