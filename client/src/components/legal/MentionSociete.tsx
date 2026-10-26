"use client";

import { AC } from "@/components/legal/LegalPage";
import { useReglagesSite, type ReglagesSite } from "@/lib/site";

/**
 * Legal number read from the API settings (SOCIETE_… variables of server/.env): filling the variable in when
 * the time comes is enough, without touching the code. Shows "to be completed" while it is empty.
 */
export default function MentionSociete({ cle, libelle }: { cle: keyof ReglagesSite["mentions"]; libelle: string }) {
  const valeur = useReglagesSite().data?.mentions[cle];
  if (!valeur) return <AC>{libelle}</AC>;
  return <>{valeur}</>;
}
