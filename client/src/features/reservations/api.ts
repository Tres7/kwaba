import api from "@/lib/api";
import type { Paginated, Reservation } from "@/types/api/models";

const RESERVATIONS = "/v1/reservations";

export async function listerMesReservations() {
  return (await api.get<Paginated<Reservation>>(`${RESERVATIONS}/`)).data.results;
}

export async function lireReservation(id: string) {
  return (await api.get<Reservation>(`${RESERVATIONS}/${id}/`)).data;
}

export async function creerReservation(reservation: Record<string, unknown>) {
  return (await api.post<Reservation>(`${RESERVATIONS}/`, reservation)).data;
}

export async function annulerReservation(id: string) {
  return (await api.delete<{ rembourse?: number; numero_requis?: boolean }>(`${RESERVATIONS}/${id}/`)).data;
}

export async function annulerReservationAdmin(id: string, motif: string) {
  await api.post(`/v1/admin/reservations/${id}/annuler/`, { motif });
}
