import api from "@/lib/api";
import { urlProxy } from "@/lib/api-url";
import type { Paginated, Reservation } from "@/types/api/models";
import type { AdminReservationDetail } from "@/types/api/admin";

const RESERVATIONS = "/v1/reservations";

export async function listerMesReservations() {
  return (await api.get<Paginated<Reservation>>(`${RESERVATIONS}/`)).data.results;
}

export async function lireReservation(id: string) {
  return (await api.get<Reservation>(`${RESERVATIONS}/${id}/`)).data;
}

/** Address of the .ics file of a paid stay, opened by a plain link: the phone offers to add it to its calendar.
 * It goes through the site's proxy, which adds the session (no JavaScript download: the iPhone would not open it). */
export function lienCalendrier(id: string, langue: string) {
  return `${urlProxy(`${RESERVATIONS}/${encodeURIComponent(id)}/calendrier/`)}?langue=${langue === "en" ? "en" : "fr"}`;
}

export async function creerReservation(reservation: Record<string, unknown>) {
  return (await api.post<Reservation>(`${RESERVATIONS}/`, reservation)).data;
}

export async function annulerReservation(id: string) {
  return (await api.delete<{ rembourse?: number; numero_requis?: boolean }>(`${RESERVATIONS}/${id}/`)).data;
}

export async function lireReservationAdmin(id: string) {
  return (await api.get<AdminReservationDetail>(`/v1/admin/reservations/${id}/`)).data;
}

export async function annulerReservationAdmin(id: string, motif: string) {
  await api.post(`/v1/admin/reservations/${id}/annuler/`, { motif });
}
