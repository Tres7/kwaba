import api from "@/lib/api";
import type { OngAdmin, ProjetAdmin } from "@/types/api/admin";
import type { ConfigGive, Don, ImpactGlobal, Organisation, OrganisationDetail, ReponseDons } from "./types";

const ADMIN = "/v1/admin/give";
// The API client sends JSON by default: header needed to send the files
const MULTIPART = { headers: { "Content-Type": "multipart/form-data" } };

export async function lireConfig() {
  return (await api.get<ConfigGive>("/v1/give/config/")).data;
}

export async function listerOrganisations(cause: string | null | undefined) {
  return (await api.get<{ results: Organisation[] }>("/v1/give/organisations/", { params: cause ? { cause } : {} })).data.results;
}

export async function lireOrganisation(slug: string) {
  return (await api.get<OrganisationDetail>(`/v1/give/organisations/${slug}/`)).data;
}

export async function lireImpact() {
  return (await api.get<ImpactGlobal>("/v1/give/impact/")).data;
}

export async function lireDon(id: string) {
  return (await api.get<Don>(`/v1/give/dons/${id}/`)).data;
}

export async function listerMesDons() {
  return (await api.get<ReponseDons>("/v1/give/dons/")).data;
}

/** Starts a donation: the answer gives the payment page. */
export async function demarrerDon(don: {
  organisation: string; projet: unknown; montant: number; couvre_frais: boolean; moyen: string; partage_identite: boolean;
}) {
  return (await api.post<{ id: string; url: string }>("/v1/give/dons/", don)).data;
}

export async function listerOngAdmin() {
  return (await api.get<OngAdmin[]>(`${ADMIN}/organisations/`)).data;
}

export async function listerProjetsAdmin(ongId: OngAdmin["id"]) {
  return (await api.get<ProjetAdmin[]>(`${ADMIN}/organisations/${ongId}/projets/`)).data;
}

export async function creerOng(corps: FormData) {
  await api.post(`${ADMIN}/organisations/`, corps, MULTIPART);
}

export async function modifierOng(id: OngAdmin["id"], corps: FormData) {
  await api.patch(`${ADMIN}/organisations/${id}/`, corps, MULTIPART);
}

/** Unpublish: empty date, which multipart cannot send. */
export async function depublierOng(id: OngAdmin["id"]) {
  await api.patch(`${ADMIN}/organisations/${id}/`, { verifiee_le: null });
}

export async function creerProjet(ongId: OngAdmin["id"], corps: FormData) {
  await api.post(`${ADMIN}/organisations/${ongId}/projets/`, corps, MULTIPART);
}

export async function modifierProjet(id: ProjetAdmin["id"], corps: FormData) {
  await api.patch(`${ADMIN}/projets/${id}/`, corps, MULTIPART);
}

export async function preparerReversements() {
  return (await api.post<{ dons: number }>(`${ADMIN}/reversements/preparer/`)).data;
}

export async function effectuerReversement(id: string | number, corps: FormData) {
  await api.post(`${ADMIN}/reversements/${id}/effectuer/`, corps, MULTIPART);
}
