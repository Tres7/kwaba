import { useQuery, useQueryClient } from "@tanstack/react-query";
import { listerSejoursAEvaluer } from "./api";

export const clesAvis = {
  tous: ["avis"],
  hebergement: (id: string) => ["avis", id],
  accueil: (ids: string[]) => ["avis", "accueil", ids],
  aLaisser: ["avis-a-laisser"],
};

export function useSejoursAEvaluer() {
  return useQuery({ queryKey: clesAvis.aLaisser, queryFn: listerSejoursAEvaluer });
}

/** After a new review: the listing's reviews and the stays still to review. */
export function useRafraichirAvis() {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: clesAvis.tous });
    queryClient.invalidateQueries({ queryKey: clesAvis.aLaisser });
  };
}
