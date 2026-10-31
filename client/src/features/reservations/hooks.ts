import { useQuery } from "@tanstack/react-query";
import { lireReservation, listerMesReservations } from "./api";

export const clesReservations = {
  toutes: ["reservations"],
  detail: (id: string) => ["reservation", id],
};

export function useMesReservations() {
  return useQuery({ queryKey: clesReservations.toutes, queryFn: listerMesReservations });
}

export function useReservation(id: string) {
  return useQuery({ queryKey: clesReservations.detail(id), queryFn: () => lireReservation(id), retry: false });
}
