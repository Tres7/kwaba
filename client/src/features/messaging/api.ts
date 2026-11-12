import api from "@/lib/api";
import type { Paginated } from "@/types/api/models";
import type {
  AdminReport, AdminSanction, MessagingConversation, MessagingMessage, ModerationCheck, ModerationStatus, ReportReason, UserSanction,
} from "./types";

const CONVERSATIONS = "/v1/messaging/conversations";

export async function listerConversations() {
  return (await api.get<Paginated<MessagingConversation>>(`${CONVERSATIONS}/`)).data.results;
}

export async function lireConversation(id: string) {
  return (await api.get<MessagingConversation>(`${CONVERSATIONS}/${encodeURIComponent(id)}/`)).data;
}

/** `apres`: id of the last message known, to read only the new ones. */
export async function listerMessages(id: string, apres?: number) {
  return (await api.get<Paginated<MessagingMessage>>(`${CONVERSATIONS}/${encodeURIComponent(id)}/messages/`, { params: { after: apres } })).data.results;
}

export async function envoyerMessage(id: string, content: string, confirmed = false) {
  const body = confirmed ? { content, confirmed: true } : { content };
  return (await api.post<MessagingMessage & { masked?: boolean }>(`${CONVERSATIONS}/${encodeURIComponent(id)}/messages/`, body)).data;
}

export async function marquerLu(id: string, jusquA: number) {
  await api.post(`${CONVERSATIONS}/${encodeURIComponent(id)}/read/`, { up_to_id: jusquA });
}

export async function compterNonLus() {
  return (await api.get<{ unread_count: number }>("/v1/messaging/unread-count/")).data.unread_count;
}

/** Back-office: alert about contact details shared in a conversation. */
export async function traiterAlerteFraude(id: number, note: string) {
  await api.post(`/v1/admin/anti-fraude/${id}/traiter/`, { note });
}

/** Idempotent: returns the existing thread if this host was already contacted for this listing. */
export async function contacterHote(hebergementId: string) {
  return (await api.post<MessagingConversation>(`${CONVERSATIONS}/`, { hebergement_id: hebergementId })).data;
}

/** Opens (or finds) the conversation with the traveller of this booking. */
export async function contacterVoyageur(reservationId: string) {
  return (await api.post<MessagingConversation>(`${CONVERSATIONS}/avec-voyageur/`, { reservation_id: reservationId })).data;
}

const MODERATION = "/v1/messaging/moderation";
const ADMIN_MODERATION = "/v1/admin/anti-fraude";

export async function checkDraft(content: string) {
  return (await api.post<ModerationCheck>(`${MODERATION}/check/`, { content })).data;
}

export async function reportFalsePositive(conversationId: string, content: string) {
  await api.post(`${CONVERSATIONS}/${encodeURIComponent(conversationId)}/false-positive/`, { content });
}

export async function reportMessage(conversationId: string, messageId: number, reason: ReportReason, details: string) {
  await api.post(`${CONVERSATIONS}/${encodeURIComponent(conversationId)}/messages/${messageId}/report/`, { reason, details });
}

export async function getModerationStatus() {
  return (await api.get<ModerationStatus>(`${MODERATION}/status/`)).data;
}

export async function contestSanction(id: number, text: string) {
  return (await api.post<UserSanction>(`${MODERATION}/sanctions/${id}/contest/`, { text })).data;
}

export async function getReport(id: number) {
  return (await api.get<AdminReport>(`${ADMIN_MODERATION}/reports/${id}/`)).data;
}

export async function confirmReport(id: number, note: string) {
  return (await api.post<AdminSanction>(`${ADMIN_MODERATION}/reports/${id}/confirm/`, { note })).data;
}

export async function rejectReport(id: number, note: string) {
  await api.post(`${ADMIN_MODERATION}/reports/${id}/reject/`, { note });
}

export async function setReportLegalHold(id: number, hold: boolean) {
  await api.post(`${ADMIN_MODERATION}/reports/${id}/legal-hold/`, { hold });
}

export async function getSanction(id: number) {
  return (await api.get<AdminSanction>(`${ADMIN_MODERATION}/sanctions/${id}/`)).data;
}

export async function reviewContest(id: number, accept: boolean, note: string) {
  return (await api.post<AdminSanction>(`${ADMIN_MODERATION}/sanctions/${id}/contest/`, { accept, note })).data;
}

export async function liftSanction(id: number, endsAt?: string) {
  return (await api.post<AdminSanction>(`${ADMIN_MODERATION}/sanctions/${id}/lift/`, endsAt ? { ends_at: endsAt } : {})).data;
}
