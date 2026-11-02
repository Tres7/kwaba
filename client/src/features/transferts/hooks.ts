import { useQuery } from "@tanstack/react-query";
import { listerAeroportsAdmin, listerChauffeurs } from "./api";

export const clesTransferts = {
  tous: ["transferts"],
  admin: ["admin", "transferts"],
};

export function useAeroportsAdmin() {
  return useQuery({ queryKey: [...clesTransferts.admin, "aeroports"], queryFn: listerAeroportsAdmin });
}

export function useChauffeurs() {
  return useQuery({ queryKey: [...clesTransferts.admin, "chauffeurs"], queryFn: listerChauffeurs });
}
