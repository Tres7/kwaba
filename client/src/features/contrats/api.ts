import api from "@/lib/api";
import { telechargerPdf } from "@/lib/documents";
import type { ContratPublic, Preinscription, SignatureContrat } from "./types";

const SIGNATURE = "/v1/contrats/signature";
const HOTE = "/v1/contrats/hote";
const PREINSCRIPTION = "/v1/contrats/preinscription/";
const ADMIN = "/v1/admin/contrats";

export async function lireContrat(jeton: string) {
  return (await api.get<ContratPublic>(`${SIGNATURE}/${jeton}/`)).data;
}

export async function signerContrat(jeton: string, signature: SignatureContrat) {
  return (await api.post<ContratPublic>(`${SIGNATURE}/${jeton}/signer/`, signature)).data;
}

export function telechargerContrat(jeton: string, reference: string | null) {
  return telechargerPdf(`${SIGNATURE}/${jeton}/pdf/`, `contrat-${reference}.pdf`);
}

export async function lireContratHote() {
  return (await api.get<ContratPublic>(`${HOTE}/`)).data;
}

export async function signerContratHote(signature: SignatureContrat & { version?: number }) {
  return (await api.post<ContratPublic>(`${HOTE}/signer/`, signature)).data;
}

export function telechargerContratHote() {
  return telechargerPdf(`${HOTE}/pdf/`, "contrat-hote.pdf");
}

export async function lirePreinscription() {
  return (await api.get<Preinscription>(PREINSCRIPTION)).data;
}

export async function accepterPreinscription(version: Preinscription["version"], langue: Preinscription["langue"]) {
  await api.post(PREINSCRIPTION, { accepte: true, version, langue });
}

export async function listerParties<T>(type: string, q: string) {
  return (await api.get<T[]>(`${ADMIN}/parties/`, { params: { type, q } })).data;
}

export async function creerContrat<T>(type: string, partieId: string) {
  return (await api.post<T>(`${ADMIN}/`, { type, partie_id: partieId })).data;
}

export async function agirSurContrat(id: string, action: "renvoyer" | "annuler", motif?: string) {
  await api.post(`${ADMIN}/${id}/${action}/`, motif ? { motif } : {});
}

export function telechargerContratAdmin(c: { id: string; reference: string }) {
  return telechargerPdf(`${ADMIN}/${c.id}/pdf/`, `contrat-${c.reference}.pdf`);
}

export async function listerModeles<T>() {
  return (await api.get<{ modeles: T[]; variables: Record<string, string> }>(`${ADMIN}/modeles/`)).data;
}

export async function enregistrerModele<T>(type: string, modele: { titre: string; corps: string }) {
  return (await api.put<T>(`${ADMIN}/modeles/${type}/`, modele)).data;
}
