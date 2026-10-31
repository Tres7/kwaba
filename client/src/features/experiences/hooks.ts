import { useQuery, useQueryClient } from "@tanstack/react-query";
import { listerExperiences, listerExperiencesAdmin } from "./api";

const CLE_ADMIN = ["admin", "experiences"];

/** Guide managed from the back-office. */
export function useExperiences() {
  return useQuery({ queryKey: ["experiences"], queryFn: listerExperiences, staleTime: 5 * 60_000 });
}

export function useExperiencesAdmin() {
  return useQuery({ queryKey: CLE_ADMIN, queryFn: listerExperiencesAdmin });
}

export function useRafraichirExperiencesAdmin() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: CLE_ADMIN });
}
