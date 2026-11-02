import { useQuery } from "@tanstack/react-query";
import { lireCompteurs } from "./api";

export interface CompteursVerification {
  /** Identity documents sent by hosts, not checked yet. */
  pieces: number;
  /** Listings an agent can visit now. */
  visites: number;
  total: number;
}

/** What waits for agents and admins, refreshed every minute (also in a background tab, for the title counter). */
export function useCompteursVerification(actif: boolean) {
  return useQuery({
    queryKey: ["verification", "compteurs"],
    queryFn: lireCompteurs,
    enabled: actif,
    refetchInterval: 60_000,
    refetchIntervalInBackground: true,
    refetchOnWindowFocus: true,
  });
}
