import { useQuery } from "@tanstack/react-query";
import { lireMoi } from "./api";

export const CLE_MOI = ["me"];

export function useMoi() {
  return useQuery({ queryKey: CLE_MOI, queryFn: lireMoi });
}
