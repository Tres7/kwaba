import api from "@/lib/api";
import type { Favori, Paginated } from "@/types/api/models";

export async function listerFavoris() {
  return (await api.get<Paginated<Favori>>("/v1/favoris/")).data.results;
}

export async function ajouterFavori(hebergementId: string) {
  await api.post("/v1/favoris/", { hebergement: hebergementId });
}

export async function retirerFavori(hebergementId: string) {
  await api.delete(`/v1/favoris/${hebergementId}/`);
}
