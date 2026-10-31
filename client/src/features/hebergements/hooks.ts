import { useQuery } from "@tanstack/react-query";
import { compterLogements, lireHebergement, lirePrelancement, listerVilles } from "./api";

export const clesHebergements = {
  tous: ["hebergements"],
  villes: ["villes"],
  mes: ["hebergements", "mine"],
  fiche: (id: string) => ["hebergement", id],
  ficheHote: (id: string) => ["hebergement", id, "hote"],
  disponibilites: (id: string) => ["disponibilites", id],
  types: (id: string) => ["types-logement", id],
};

/** Empty field of the search: popular destinations, also shown on the home page. */
export function useVilles(actif = true) {
  return useQuery({ queryKey: clesHebergements.villes, queryFn: listerVilles, enabled: actif });
}

/** Listing as its host sees it. */
export function useHebergementHote(id: string) {
  return useQuery({ queryKey: clesHebergements.ficheHote(id), queryFn: () => lireHebergement(id) });
}

/**
 * Pre-launch mode, read from the API (PRELANCEMENT in the server environment): switching it needs no new client
 * image. False while unknown or if the API cannot be reached, so the usual site is shown by default.
 */
export function usePrelancement(): boolean {
  const { data } = useQuery({ queryKey: ["lancement", "prelancement"], queryFn: lirePrelancement, staleTime: 5 * 60_000 });
  return data === true;
}

/** True while no listing is published (the window and the banner disappear by themselves with the first one). */
export function useAucunLogement(): boolean {
  const { data } = useQuery({
    queryKey: ["lancement", "aucun-logement"],
    queryFn: async () => (await compterLogements()) === 0,
    staleTime: 5 * 60_000,
  });
  return data === true;
}
