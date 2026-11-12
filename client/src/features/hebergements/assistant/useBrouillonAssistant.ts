"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { enregistrerEtape, lireBrouillon } from "../api";
import type { DonneesAnnonce } from "../brouillons";
import { clesHebergements } from "../hooks";

export type EtatSauvegarde = "enregistre" | "en_cours" | "hors_ligne";

// Pause in typing before saving: one request per sentence rather than per letter
const PAUSE_SAISIE_MS = 900;
const NOUVEL_ESSAI_MS = 10_000;

/**
 * The draft as the host fills it in. Answers appear at once and leave in the background, one request at a time so that
 * an older one never overwrites a newer one. Without a network, they stay here and leave with the next attempt.
 */
export function useBrouillonAssistant(id: string) {
  const { data: brouillon, isError } = useQuery({
    queryKey: clesHebergements.brouillon(id), queryFn: () => lireBrouillon(id), staleTime: Infinity, gcTime: 0, retry: 1,
  });
  const [donnees, setDonnees] = useState<DonneesAnnonce | null>(null);
  const [erreurs, setErreurs] = useState<Record<string, string[]>>({});
  const [etat, setEtat] = useState<EtatSauvegarde>("enregistre");
  const attente = useRef<DonneesAnnonce>({});
  const file = useRef<Promise<void>>(Promise.resolve());
  const minuteur = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const retry = useRef<(etape?: string) => Promise<void>>(() => Promise.resolve());

  useEffect(() => {
    if (brouillon) setDonnees((actuelles) => actuelles ?? brouillon.donnees);
  }, [brouillon]);

  const envoyer = useCallback((etape?: string): Promise<void> => {
    clearTimeout(minuteur.current);
    file.current = file.current.then(async () => {
      const champs = attente.current;
      if (!Object.keys(champs).length && etape === undefined) return;
      attente.current = {};
      setEtat("en_cours");
      try {
        const reponse = await enregistrerEtape(id, champs, etape);
        setErreurs(reponse.erreurs);
        setEtat("enregistre");
      } catch {
        // Newer answers typed in the meantime win over the ones put back
        attente.current = { ...champs, ...attente.current };
        setEtat("hors_ligne");
        minuteur.current = setTimeout(() => void retry.current(etape), NOUVEL_ESSAI_MS);
      }
    });
    return file.current;
  }, [id]);

  useEffect(() => {
    retry.current = envoyer;
  }, [envoyer]);

  const modifier = useCallback((champs: DonneesAnnonce) => {
    setDonnees((actuelles) => ({ ...actuelles, ...champs }));
    attente.current = { ...attente.current, ...champs };
    clearTimeout(minuteur.current);
    minuteur.current = setTimeout(() => void envoyer(), PAUSE_SAISIE_MS);
  }, [envoyer]);

  useEffect(() => {
    const reprendre = () => void envoyer();
    window.addEventListener("online", reprendre);
    return () => {
      window.removeEventListener("online", reprendre);
      clearTimeout(minuteur.current);
    };
  }, [envoyer]);

  return { donnees, etapeEnregistree: brouillon?.etape, introuvable: isError, erreurs, etat, modifier, envoyer };
}
