import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { Favori } from "@/types/api/models";
import { listerFavoris } from "./api";

const CLE = ["favoris"];

export function useFavoris() {
  return useQuery({ queryKey: CLE, queryFn: listerFavoris });
}

/** Takes a listing out of the list already displayed, without reading it again. */
export function useOterDeLaListe() {
  const queryClient = useQueryClient();
  return (hebergementId: string) =>
    queryClient.setQueryData<Favori[]>(CLE, (prev) => prev?.filter((f) => f.hebergement !== hebergementId));
}
