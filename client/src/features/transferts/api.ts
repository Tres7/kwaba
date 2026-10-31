import api from "@/lib/api";
import type { AeroportAdmin, ChauffeurAdmin } from "@/types/api/admin";
import type { Paginated } from "@/types/api/models";
import type { Aeroport, Devis, Transfert } from "./types";

const TRANSFERTS = "/v1/transferts";
const ADMIN = "/v1/admin/transferts";

export async function listerMesTransferts() {
  return (await api.get<Paginated<Transfert>>(`${TRANSFERTS}/`)).data.results;
}

export async function lireTransfert(id: string) {
  return (await api.get<Transfert>(`${TRANSFERTS}/${id}/`)).data;
}

export async function listerAeroports() {
  return (await api.get<Aeroport[]>(`${TRANSFERTS}/aeroports/`)).data;
}

export async function calculerDevis(params: { aeroport: string; arrivee: string; passagers: number; bagages: number }) {
  return (await api.get<Devis>(`${TRANSFERTS}/devis/`, { params })).data;
}

export async function creerTransfert(transfert: Record<string, unknown>) {
  return (await api.post<Transfert>(`${TRANSFERTS}/`, transfert)).data;
}

export async function annulerTransfert(id: string) {
  return (await api.delete<{ rembourse: number; numero_requis: boolean }>(`${TRANSFERTS}/${id}/`)).data;
}

export const adresseCompteRemboursement = (id: string) => `${TRANSFERTS}/${id}/compte-remboursement/`;

export async function listerAeroportsAdmin() {
  return (await api.get<AeroportAdmin[]>(`${ADMIN}/aeroports/`)).data;
}

export async function creerAeroport(aeroport: unknown) {
  return (await api.post<AeroportAdmin>(`${ADMIN}/aeroports/`, aeroport)).data;
}

export async function modifierAeroport(code: string, aeroport: unknown) {
  await api.patch(`${ADMIN}/aeroports/${code}/`, aeroport);
}

export async function enregistrerTarifs(code: string, tarifs: unknown[]) {
  await api.put(`${ADMIN}/aeroports/${code}/tarifs/`, tarifs);
}

export async function listerChauffeurs() {
  return (await api.get<ChauffeurAdmin[]>(`${ADMIN}/chauffeurs/`)).data;
}

export async function creerChauffeur(chauffeur: unknown) {
  await api.post(`${ADMIN}/chauffeurs/`, chauffeur);
}

export async function modifierChauffeur(id: ChauffeurAdmin["id"], chauffeur: unknown) {
  await api.patch(`${ADMIN}/chauffeurs/${id}/`, chauffeur);
}

export async function listerChauffeursDisponibles(transfertId: string) {
  return (await api.get<{ id: number; nom: string; telephone: string; vehicule: string }[]>(`${ADMIN}/transferts/${transfertId}/chauffeurs/`)).data;
}

export async function attribuerChauffeur(transfertId: string, chauffeur: number) {
  await api.post(`${ADMIN}/transferts/${transfertId}/attribuer/`, { chauffeur });
}

export async function annulerTransfertAdmin(transfertId: string, motif: string) {
  await api.post(`${ADMIN}/transferts/${transfertId}/annuler/`, { motif });
}
