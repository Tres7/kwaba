import { useQuery } from "@tanstack/react-query";
import type { OngAdmin } from "@/types/api/admin";
import { lireConfig, lireImpact, lireOrganisation, listerMesDons, listerOngAdmin, listerOrganisations, listerProjetsAdmin } from "./api";

export const clesGive = {
  admin: ["admin", "give"],
  don: (id: string) => ["give", "don", id],
};

/** Public donation settings: suggested amounts, fees, transfer schedule. */
export function useConfigGive() {
  return useQuery({ queryKey: ["give", "config"], queryFn: lireConfig, staleTime: 60 * 1000 });
}

export function useOrganisations(cause: string | null | undefined) {
  return useQuery({ queryKey: ["give", "organisations", cause], queryFn: () => listerOrganisations(cause) });
}

export function useOrganisation(slug: string) {
  return useQuery({ queryKey: ["give", "organisation", slug], queryFn: () => lireOrganisation(slug), retry: false });
}

export function useImpactGive() {
  return useQuery({ queryKey: ["give", "impact"], queryFn: lireImpact });
}

export function useMesDons() {
  return useQuery({ queryKey: ["give", "dons"], queryFn: listerMesDons });
}

export function useOngAdmin() {
  return useQuery({ queryKey: [...clesGive.admin, "organisations"], queryFn: listerOngAdmin });
}

export function useProjetsAdmin(ong: OngAdmin | null) {
  return useQuery({
    queryKey: [...clesGive.admin, "projets", ong?.id],
    queryFn: () => listerProjetsAdmin((ong as OngAdmin).id),
    enabled: !!ong,
  });
}
