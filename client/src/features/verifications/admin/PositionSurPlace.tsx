"use client";

import { AlertTriangle, LocateFixed, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { distanceMetres, ECART_A_VERIFIER_M, formatDistance, type PositionMesuree } from "./position";
import { useGps } from "./useGps";

/** "Take my position" in front of the listing: the phone's GPS replaces the host's point once the visit is validated. */
export default function PositionSurPlace({ pointHote, valeur, onChange, desactive }: {
  pointHote: { lat: number; lng: number } | null;
  valeur: PositionMesuree | null;
  onChange: (position: PositionMesuree | null) => void;
  desactive: boolean;
}) {
  const { relever, recherche, erreur } = useGps(onChange);
  const ecart = valeur && pointHote ? distanceMetres(pointHote, { lat: valeur.latitude, lng: valeur.longitude }) : null;

  return (
    <div className="pt-1 space-y-2">
      <span className="block text-xs font-bold uppercase tracking-wide text-gray-500">Position du logement (facultatif)</span>
      {valeur ? (
        <div className={cn("rounded-xl px-3 py-3 text-sm",
          ecart !== null && ecart >= ECART_A_VERIFIER_M ? "bg-amber-50 text-amber-900" : "bg-green-50 text-green-800")}>
          <div className="flex items-start justify-between gap-2">
            <p>
              Position relevée (± {Math.round(valeur.precision)} m)
              {ecart !== null ? `, à ${formatDistance(ecart)} du point placé par l'hôte.` : ". L'hôte n'avait placé aucun point."}
            </p>
            {!desactive && (
              <button type="button" onClick={() => onChange(null)} aria-label="Retirer la position relevée" className="p-1 -m-1">
                <X size={16} aria-hidden />
              </button>
            )}
          </div>
          {ecart !== null && ecart >= ECART_A_VERIFIER_M && (
            <p className="mt-1 flex items-start gap-1.5 font-semibold">
              <AlertTriangle size={15} className="mt-0.5 flex-shrink-0" aria-hidden />
              Écart important : vérifiez que vous êtes bien devant ce logement.
            </p>
          )}
          <p className="mt-1 text-xs opacity-80">À la validation, elle remplace le point de l&apos;hôte. Les voyageurs ne voient qu&apos;une zone approximative.</p>
        </div>
      ) : (
        <p className="text-xs text-gray-500">Devant l&apos;entrée, relevez la position avec votre téléphone : elle remplacera le point placé par l&apos;hôte sur la carte.</p>
      )}
      <button type="button" onClick={relever} disabled={desactive || recherche}
        className="w-full flex items-center justify-center gap-2 px-4 py-4 rounded-xl border border-dashed border-gray-300 text-sm font-semibold text-gray-600 disabled:opacity-50">
        <LocateFixed size={20} aria-hidden /> {recherche ? "Recherche du GPS…" : valeur ? "Reprendre ma position" : "Prendre ma position"}
      </button>
      {erreur && <p role="alert" className="text-sm text-red-700">{erreur}</p>}
    </div>
  );
}
