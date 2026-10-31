import { useQuery } from "@tanstack/react-query";
import { lireMessages, lireStatut, listerConversations } from "./api";

export const clesConcierge = {
  statut: ["concierge", "statut"],
  conversations: ["concierge", "conversations"],
  conversation: (id: string | null) => ["concierge", "conversation", id],
};

export function useStatutConcierge() {
  return useQuery({ queryKey: clesConcierge.statut, queryFn: lireStatut });
}

export function useConversationsConcierge(connecte: boolean) {
  return useQuery({ queryKey: clesConcierge.conversations, queryFn: listerConversations, enabled: connecte });
}

export function useMessagesConcierge(conversationId: string | null, connecte: boolean) {
  return useQuery({
    queryKey: clesConcierge.conversation(conversationId),
    queryFn: () => lireMessages(conversationId as string),
    enabled: connecte && !!conversationId,
  });
}
