import api from "@/lib/api";
import { urlProxy } from "@/lib/api-url";
import type {
  AgendaSettings, AgendaSettingsValues, AgentRef, Appointment, AppointmentDetail, Availability, Coverage, HostAppointment, MyVisit, WeeklySlot,
} from "./types";

const AGENDA = "/v1/agenda";
const VERIFICATIONS = "/v1/verifications";

export async function readAvailability() {
  return (await api.get<Availability>(`${AGENDA}/availability/`)).data;
}

export async function saveWeek(body: { cities: string[]; weekly_slots: WeeklySlot[] }) {
  return (await api.put<Availability>(`${AGENDA}/availability/`, body)).data;
}

export async function addException(body: { day: string; kind: "block" | "extra"; start?: string; end?: string }) {
  return (await api.post<Availability>(`${AGENDA}/availability/exceptions/`, body)).data;
}

export async function deleteException(id: number) {
  return (await api.delete<Availability>(`${AGENDA}/availability/exceptions/${id}/`)).data;
}

export async function setDayLimit(day: string, maxVisits: number | null) {
  return (await api.put<Availability>(`${AGENDA}/availability/day-limits/${day}/`, { max_visits: maxVisits })).data;
}

export async function listAppointments(params: { start: string; end: string; agent?: string }) {
  return (await api.get<{ results: Appointment[] }>(`${AGENDA}/appointments/`, { params })).data.results;
}

export async function readAppointment(id: string) {
  return (await api.get<AppointmentDetail>(`${AGENDA}/appointments/${encodeURIComponent(id)}/`)).data;
}

export async function onTheWay(id: string) {
  return (await api.post<Appointment>(`${AGENDA}/appointments/${encodeURIComponent(id)}/on-the-way/`)).data;
}

export function appointmentIcsUrl(id: string) {
  return urlProxy(`${AGENDA}/appointments/${encodeURIComponent(id)}/ics/`);
}

export async function readFeed() {
  return (await api.get<{ url: string }>(`${AGENDA}/feed/`)).data;
}

export async function regenerateFeed() {
  return (await api.post<{ url: string }>(`${AGENDA}/feed/`)).data;
}

export async function readCoverage() {
  return (await api.get<Coverage>(`${AGENDA}/admin/coverage/`)).data;
}

export async function listAgents() {
  return (await api.get<{ results: AgentRef[] }>(`${AGENDA}/admin/agents/`)).data.results;
}

export async function cancelAppointment(id: string, reason: string) {
  await api.post(`${VERIFICATIONS}/appointments/${encodeURIComponent(id)}/cancel/`, { reason });
}

export async function reassignAppointment(id: string, agentId: string) {
  await api.post(`${VERIFICATIONS}/appointments/${encodeURIComponent(id)}/reassign/`, { agent_id: agentId });
}

export async function bookByPhone(listingId: string, start: string) {
  await api.post(`${VERIFICATIONS}/listings/${encodeURIComponent(listingId)}/appointment/`, { start });
}

export async function readMyVisit() {
  return (await api.get<MyVisit>(`${VERIFICATIONS}/visit/`)).data;
}

export async function listFreeSlots(listingIds: string[]) {
  return (await api.get<{ slots: string[] }>(`${VERIFICATIONS}/visit/slots/`, {
    params: { listings: listingIds.join(",") },
  })).data.slots;
}

export async function bookVisit(listingIds: string[], start: string) {
  return (await api.post<HostAppointment>(`${VERIFICATIONS}/visit/book/`, { listings: listingIds, start })).data;
}

export async function listMoveSlots(appointmentId: string) {
  return (await api.get<{ slots: string[] }>(
    `${VERIFICATIONS}/visit/appointments/${encodeURIComponent(appointmentId)}/slots/`)).data.slots;
}

export async function moveVisit(appointmentId: string, start: string) {
  return (await api.post<HostAppointment>(
    `${VERIFICATIONS}/visit/appointments/${encodeURIComponent(appointmentId)}/move/`, { start })).data;
}

export async function readAgendaSettings() {
  return (await api.get<AgendaSettings>("/v1/admin/agenda/settings/")).data;
}

export async function saveAgendaSettings(values: Partial<AgendaSettingsValues>) {
  return (await api.put<AgendaSettings>("/v1/admin/agenda/settings/", values)).data;
}

export async function concludePostCheck(id: string, compliant: boolean, reason = "") {
  await api.post(`${VERIFICATIONS}/appointments/${encodeURIComponent(id)}/post-check/`, { compliant, reason });
}
