import api from "@/lib/api";
import type { AnnoncePosition, CompteursVerification, MissionResume, TableauAgent } from "./hooks";

const VERIFICATIONS = "/v1/verifications";
const MISSIONS = "/v1/agent/missions";
// The API client sends JSON by default: header needed to send the files
const MULTIPART = { headers: { "Content-Type": "multipart/form-data" } };

export async function lireTableauAgent() {
  return (await api.get<TableauAgent>("/v1/agent/tableau/")).data;
}

export async function listerMissions(params: Record<string, string>) {
  return (await api.get<{ results: MissionResume[]; count: number }>(`${MISSIONS}/`, { params })).data;
}

export async function lireMission<T>(type: string, cible: string) {
  return (await api.get<T>(`${MISSIONS}/${encodeURIComponent(type)}/${encodeURIComponent(cible)}/`)).data;
}

export async function agirSurMission(type: string, cible: string, action: "prendre" | "liberer") {
  await api.post(`${MISSIONS}/${encodeURIComponent(type)}/${encodeURIComponent(cible)}/${action}/`);
}

export async function lireCompteurs() {
  return (await api.get<CompteursVerification>(`${VERIFICATIONS}/compteurs/`)).data;
}

export async function deciderVisite(logementId: string, decision: FormData) {
  await api.post(`${VERIFICATIONS}/visites/${logementId}/decision/`, decision, MULTIPART);
}

/** Photos added to a verified listing: the ones in `retirer` leave it, the host is told why. */
export async function deciderPhotos(hebergementId: string, decision: { retirer: string[]; motif: string }) {
  await api.post(`${VERIFICATIONS}/photos/${encodeURIComponent(hebergementId)}/decision/`, decision);
}

export async function deciderPiece(hoteId: string, decision: { decision: string; motif: string }) {
  await api.post(`${VERIFICATIONS}/identites/${hoteId}/decision/`, decision);
}

/** Read with the agent's token: never a public address. */
export async function lireFichierPiece(hoteId: string) {
  return (await api.get<Blob>(`${VERIFICATIONS}/identite/${hoteId}/fichier/`, { responseType: "blob" })).data;
}

export async function lireMaPiece<T>() {
  return (await api.get<T>(`${VERIFICATIONS}/identite/`)).data;
}

export async function envoyerMaPiece(piece: FormData) {
  await api.post(`${VERIFICATIONS}/identite/`, piece, MULTIPART);
}

/** Verified listings whose position an agent can correct (by default, those still at the host's point). */
export async function listerPositions(params: { q?: string; toutes?: boolean }) {
  const filtres = { ...(params.q ? { q: params.q } : {}), ...(params.toutes ? { toutes: "1" } : {}) };
  return (await api.get<{ a_relever: number; results: AnnoncePosition[] }>(`${VERIFICATIONS}/positions/`, { params: filtres })).data;
}

/** Latitude and longitude of a pasted Google Maps link, WhatsApp location or coordinates. */
export async function lirePosition(texte: string) {
  return (await api.post<{ latitude: number; longitude: number }>(`${VERIFICATIONS}/positions/lire/`, { texte })).data;
}

/** Replaces the position of a verified listing (it stays online). */
export async function corrigerPosition(hebergementId: string, corps: {
  latitude: number; longitude: number; precision?: number | null; source: "gps" | "texte";
}) {
  return (await api.post<{ ecart_m: number | null }>(`${VERIFICATIONS}/positions/${encodeURIComponent(hebergementId)}/`, corps)).data;
}
