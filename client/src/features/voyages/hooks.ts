import { useQuery } from "@tanstack/react-query";
import { listerVoyages } from "./api";

export const clesVoyages = {
  tous: ["voyages"],
  voyage: (id: string) => ["voyage", id],
};

export function useMesVoyages(actif: boolean) {
  return useQuery({ queryKey: clesVoyages.tous, queryFn: listerVoyages, enabled: actif });
}
