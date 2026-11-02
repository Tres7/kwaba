import api from "@/lib/api";
import type { Avis, AvisPage, CritereAvis, Paginated, SejourAEvaluer } from "@/types/api/models";

export async function listerAvis(hebergement: string, page: { limit: number; offset?: number }) {
  return (await api.get<AvisPage>("/v1/avis/", { params: { hebergement, ...page } })).data;
}

export async function repondreAvis(avisId: string, reponse: string) {
  return (await api.post<Avis>(`/v1/avis/${avisId}/reponse/`, { reponse })).data;
}

export async function listerSejoursAEvaluer() {
  return (await api.get<Paginated<SejourAEvaluer>>("/v1/avis/a-laisser/")).data.results;
}

export async function publierAvis(avis: { reservation: string; note: number; commentaire: string } & Partial<Record<CritereAvis, number>>) {
  await api.post("/v1/avis/", avis);
}

export async function supprimerAvisAdmin(avisId: string, motif: string) {
  await api.delete(`/v1/admin/avis/${avisId}/`, { params: { motif } });
}
