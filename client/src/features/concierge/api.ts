import api from "@/lib/api";
import { urlProxy } from "@/lib/api-url";
import type { CarteTogether, ConversationResume, MessageConcierge } from "./types";

const CONVERSATIONS = "/v1/concierge/conversations";

export async function lireStatut() {
  return (await api.get<{ actif: boolean }>("/v1/concierge/statut/")).data;
}

export async function listerConversations() {
  return (await api.get<{ results: ConversationResume[] }>(`${CONVERSATIONS}/`)).data.results;
}

export async function lireMessages(conversationId: string) {
  return (await api.get<{ messages: MessageConcierge[] }>(`${CONVERSATIONS}/${conversationId}/`)).data.messages;
}

export async function creerConversation() {
  return (await api.post<{ id: string }>(`${CONVERSATIONS}/`)).data.id;
}

export async function supprimerConversation(id: string) {
  await api.delete(`${CONVERSATIONS}/${id}/`);
}

/** The answer comes as a stream, which axios cannot read in the browser: the only `fetch` of the site's API calls. */
export async function posterMessage(conversationId: string, texte: string, langue: string, erreurParDefaut: string) {
  const reponse = await fetch(urlProxy(`${CONVERSATIONS}/${conversationId}/messages/`), {
    method: "POST",
    headers: { "Content-Type": "application/json", "Accept-Language": langue },
    body: JSON.stringify({ texte }),
  });
  if (!reponse.ok) {
    const corps = await reponse.json().catch(() => ({}));
    throw new Error(corps.detail || corps.texte?.[0] || erreurParDefaut);
  }
  return reponse;
}

/** Group trip suggested by the Concierge. A listing refused by the API does not stop the others. */
export async function creerVoyageDeGroupe(c: CarteTogether) {
  const { id } = (await api.post<{ id: string }>("/v1/voyages/", {
    nom: c.nom, destination: c.destination, date_debut: c.arrivee, date_fin: c.depart, nb_voyageurs: c.voyageurs,
  })).data;
  await Promise.allSettled(c.logements.map((l) => api.post(`/v1/voyages/${id}/propositions/`, { hebergement: l.id })));
  return id;
}
