import api from "@/lib/api";
import type { Paginated } from "@/types/api/models";
import type { MessagingConversation, MessagingMessage } from "./types";

const CONVERSATIONS = "/v1/messaging/conversations";

export async function listerConversations() {
  return (await api.get<Paginated<MessagingConversation>>(`${CONVERSATIONS}/`)).data.results;
}

export async function lireConversation(id: string) {
  return (await api.get<MessagingConversation>(`${CONVERSATIONS}/${id}/`)).data;
}

/** `apres`: id of the last message known, to read only the new ones. */
export async function listerMessages(id: string, apres?: number) {
  return (await api.get<Paginated<MessagingMessage>>(`${CONVERSATIONS}/${id}/messages/`, { params: { after: apres } })).data.results;
}

export async function envoyerMessage(id: string, content: string) {
  return (await api.post<MessagingMessage & { masked?: boolean }>(`${CONVERSATIONS}/${id}/messages/`, { content })).data;
}

export async function marquerLu(id: string, jusquA: number) {
  await api.post(`${CONVERSATIONS}/${id}/read/`, { up_to_id: jusquA });
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
