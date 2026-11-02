import api from "@/lib/api";
import type { CategorieVehicule as CategorieAdmin, ChoixAttribution, LieuRemise, Loueur, PhotoVehicule, ReglesLocation } from "@/types/api/admin";
import type { CatalogueLocation, DevisLocation, Location, MonChauffeur } from "./types";

const LOCATIONS = "/v1/locations";
const ADMIN = "/v1/admin/location";
const photos = (categorieId: number) => `${ADMIN}/categories/${categorieId}/photos/`;

export async function lireCatalogue() {
  return (await api.get<CatalogueLocation>(`${LOCATIONS}/catalogue/`)).data;
}

export async function listerMesChauffeurs() {
  return (await api.get<MonChauffeur[]>(`${LOCATIONS}/mes-chauffeurs/`)).data;
}

export async function calculerDevisLocation(params: Record<string, unknown>) {
  return (await api.get<DevisLocation>(`${LOCATIONS}/devis/`, { params })).data;
}

export async function creerLocation(location: Record<string, unknown>) {
  return (await api.post<Location>(`${LOCATIONS}/`, location)).data;
}

export async function listerMesLocations() {
  return (await api.get<{ results: Location[] }>(`${LOCATIONS}/`)).data.results;
}

export async function lireLocation(id: string) {
  return (await api.get<Location>(`${LOCATIONS}/${id}/`)).data;
}

export async function annulerLocation(id: string) {
  return (await api.delete<{ rembourse: number; numero_requis: boolean }>(`${LOCATIONS}/${id}/`)).data;
}

export const adresseCompteRemboursement = (id: string) => `${LOCATIONS}/${id}/compte-remboursement/`;

export async function listerCategories() {
  return (await api.get<CategorieAdmin[]>(`${ADMIN}/categories/`)).data;
}

export async function creerCategorie(categorie: unknown) {
  return (await api.post<CategorieAdmin>(`${ADMIN}/categories/`, categorie)).data;
}

export async function modifierCategorie(id: number, categorie: unknown) {
  await api.patch(`${ADMIN}/categories/${id}/`, categorie);
}

/** One request per photo: several at once would exceed the size accepted by the server. */
export async function ajouterPhoto(categorieId: number, corps: FormData) {
  return (await api.post<PhotoVehicule[]>(photos(categorieId), corps, { headers: { "Content-Type": "multipart/form-data" } })).data;
}

export async function rendrePrincipale(categorieId: number, photoId: number) {
  return (await api.patch<PhotoVehicule[]>(`${photos(categorieId)}${photoId}/`, { principale: true })).data;
}

export async function retirerPhoto(categorieId: number, photoId: number) {
  return (await api.delete<PhotoVehicule[]>(`${photos(categorieId)}${photoId}/`)).data;
}

export async function listerLoueurs() {
  return (await api.get<Loueur[]>(`${ADMIN}/loueurs/`)).data;
}

export async function creerLoueur(loueur: unknown) {
  await api.post(`${ADMIN}/loueurs/`, loueur);
}

export async function modifierLoueur(id: Loueur["id"], loueur: unknown) {
  await api.patch(`${ADMIN}/loueurs/${id}/`, loueur);
}

export async function listerLieux() {
  return (await api.get<LieuRemise[]>(`${ADMIN}/lieux/`)).data;
}

export async function creerLieu(lieu: unknown) {
  await api.post(`${ADMIN}/lieux/`, lieu);
}

export async function modifierLieu(id: number, lieu: unknown) {
  await api.patch(`${ADMIN}/lieux/${id}/`, lieu);
}

export async function lireRegles() {
  return (await api.get<ReglesLocation | null>(`${ADMIN}/regles/`)).data;
}

export async function enregistrerRegles(regles: unknown) {
  await api.put(`${ADMIN}/regles/`, regles);
}

export async function lireChoixAttribution(locationId: string) {
  return (await api.get<ChoixAttribution>(`${ADMIN}/locations/${locationId}/loueurs/`, { params: { chauffeurs: 1 } })).data;
}

export async function attribuerLocation(locationId: string, attribution: Record<string, unknown>) {
  await api.post(`${ADMIN}/locations/${locationId}/attribuer/`, attribution);
}

export async function retenirCaution(locationId: string, retenue: { montant: number; motif: string }) {
  await api.post(`${ADMIN}/locations/${locationId}/caution/`, retenue);
}

export async function annulerLocationAdmin(locationId: string, motif: string) {
  await api.post(`${ADMIN}/locations/${locationId}/annuler/`, { motif });
}
