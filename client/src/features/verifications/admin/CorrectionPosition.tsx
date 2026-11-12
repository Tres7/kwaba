"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { AlertTriangle, Check, ClipboardPaste, ExternalLink, LocateFixed } from "lucide-react";
import { apiErrorMessage } from "@/lib/api";
import { cn } from "@/lib/utils";
import { corrigerPosition, lirePosition } from "../api";
import { CLE_POSITIONS, type AnnoncePosition } from "../hooks";
import { distanceMetres, ECART_A_VERIFIER_M, formatDistance, lienCarte } from "./position";
import { useGps } from "./useGps";

interface Candidate {
  latitude: number;
  longitude: number;
  precision: number | null;
  source: "gps" | "texte";
}

/** New position of a verified listing: the phone's GPS on site, or a pasted Google Maps link, WhatsApp location or
 * coordinates. Shown with its gap from the current point and a link to check it on Google Maps before saving. */
export default function CorrectionPosition({ annonce, onTerminee }: {
  annonce: AnnoncePosition;
  onTerminee: () => void;
}) {
  const queryClient = useQueryClient();
  const [texte, setTexte] = useState("");
  const [lecture, setLecture] = useState(false);
  const [erreurTexte, setErreurTexte] = useState("");
  const [candidate, setCandidate] = useState<Candidate | null>(null);
  const [envoi, setEnvoi] = useState(false);
  const gps = useGps((p) => setCandidate({ ...p, source: "gps" }));

  const lire = async () => {
    setLecture(true);
    setErreurTexte("");
    try {
      const { latitude, longitude } = await lirePosition(texte);
      setCandidate({ latitude, longitude, precision: null, source: "texte" });
    } catch (err) {
      setErreurTexte(apiErrorMessage(err));
    } finally {
      setLecture(false);
    }
  };

  const enregistrer = async () => {
    if (!candidate) return;
    setEnvoi(true);
    try {
      await corrigerPosition(annonce.id, candidate);
      toast.success(`Position de « ${annonce.name} » enregistrée.`);
      await queryClient.invalidateQueries({ queryKey: CLE_POSITIONS });
      onTerminee();
    } catch (err) {
      toast.error(apiErrorMessage(err));
      setEnvoi(false);
    }
  };

  const point = candidate ? { lat: candidate.latitude, lng: candidate.longitude } : null;
  const ecart = point && annonce.position ? distanceMetres(annonce.position, point) : null;
  const loin = ecart !== null && ecart >= ECART_A_VERIFIER_M;

  return (
    <div className="border-t border-gray-100 pt-4 mt-3 space-y-4">
      <div className="space-y-2">
        <label htmlFor={`position-${annonce.id}`} className="block text-xs font-bold uppercase tracking-wide text-gray-500">
          Lien Google Maps, position WhatsApp ou coordonnées
        </label>
        <textarea id={`position-${annonce.id}`} value={texte} onChange={(e) => setTexte(e.target.value)} rows={2} maxLength={2000}
          placeholder="https://maps.app.goo.gl/…  ou  6.131900, 1.222800"
          className="w-full px-4 py-3 border border-gray-200 rounded-xl text-base sm:text-sm focus:outline-hidden focus:ring-2 focus:ring-primary/20 focus:border-primary" />
        {erreurTexte && <p role="alert" className="text-sm text-red-700">{erreurTexte}</p>}
        <div className="grid grid-cols-2 gap-2">
          <button type="button" onClick={lire} disabled={!texte.trim() || lecture || envoi}
            className="flex items-center justify-center gap-2 px-3 py-3 rounded-xl bg-gray-100 text-sm font-semibold text-dark disabled:opacity-50">
            <ClipboardPaste size={17} aria-hidden /> {lecture ? "Lecture…" : "Lire la position"}
          </button>
          <button type="button" onClick={gps.relever} disabled={gps.recherche || envoi}
            className="flex items-center justify-center gap-2 px-3 py-3 rounded-xl bg-gray-100 text-sm font-semibold text-dark disabled:opacity-50">
            <LocateFixed size={17} aria-hidden /> {gps.recherche ? "GPS…" : "Ma position (sur place)"}
          </button>
        </div>
        {gps.erreur && <p role="alert" className="text-sm text-red-700">{gps.erreur}</p>}
      </div>

      {candidate && point && (
        <div className={cn("rounded-xl px-3 py-3 text-sm space-y-2", loin ? "bg-amber-50 text-amber-900" : "bg-green-50 text-green-800")}>
          <p>
            <strong>Nouvelle position</strong> {candidate.source === "gps" ? `(GPS, ± ${Math.round(candidate.precision ?? 0)} m)` : "(lue dans le texte collé)"} :{" "}
            <span className="tabular-nums">{candidate.latitude.toFixed(6)}, {candidate.longitude.toFixed(6)}</span>
            {ecart !== null ? `, à ${formatDistance(ecart)} du point actuel.` : ". L'annonce n'avait aucun point."}
          </p>
          {loin && (
            <p className="flex items-start gap-1.5 font-semibold">
              <AlertTriangle size={15} className="mt-0.5 shrink-0" aria-hidden />
              Écart important : vérifiez sur la carte que c&apos;est bien ce logement.
            </p>
          )}
          <a href={lienCarte(point)} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1.5 font-bold underline">
            Vérifier sur Google Maps <ExternalLink size={14} aria-hidden />
          </a>
          <button type="button" onClick={enregistrer} disabled={envoi}
            className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-primary text-white text-sm font-bold disabled:opacity-60">
            <Check size={17} aria-hidden /> {envoi ? "Enregistrement…" : "Enregistrer cette position"}
          </button>
          <p className="text-xs opacity-80">L&apos;annonce reste en ligne. Les voyageurs ne voient qu&apos;une zone approximative autour de ce point.</p>
        </div>
      )}
    </div>
  );
}
