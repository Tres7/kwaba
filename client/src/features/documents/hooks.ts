import { useQuery } from "@tanstack/react-query";
import { lireSociete } from "./api";

export const CLE_SOCIETE = ["admin", "documents", "societe"];

export function useSociete() {
  return useQuery({ queryKey: CLE_SOCIETE, queryFn: lireSociete });
}
