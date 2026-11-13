"use client";

import { useState } from "react";
import { CheckCircle2, ExternalLink, MapPin, Search } from "lucide-react";
import { cn, formatDate } from "@/lib/utils";
import { usePositions } from "../hooks";
import CorrectionPosition from "./CorrectionPosition";
import ListeMissions from "./ListeMissions";
import { lienCarte } from "./position";

/** Positions of the listings already verified: an agent (or an admin) replaces the host's point with the one measured
 * on site, from the phone's GPS or from what they noted (Google Maps link, WhatsApp location, coordinates). */
export default function Positions() {
  const [q, setQ] = useState("");
  const [toutes, setToutes] = useState(false);
  const [ouverte, setOuverte] = useState<string | null>(null);
  const { data, isLoading, isError } = usePositions(q.trim(), toutes);

  return (
    <div>
      <h1 className="font-heading font-bold text-2xl text-dark">Positions des logements</h1>
      <p className="text-sm text-gray-500 mt-1">
        Remplacez le point placé par l&apos;hôte par la vraie position du logement. L&apos;annonce reste en ligne.
        {data && ` ${data.a_relever} annonce(s) vérifiée(s) ont encore le point de l'hôte.`}
      </p>

      <label className="relative block mt-5">
        <span className="sr-only">Rechercher par nom, ville, quartier ou hôte</span>
        <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" aria-hidden />
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Nom, ville, quartier ou hôte"
          className="w-full pl-11 pr-4 py-3 bg-surface border border-gray-200 rounded-xl text-base sm:text-sm focus:outline-hidden focus:ring-2 focus:ring-primary/20 focus:border-primary" />
      </label>
      <label className="inline-flex items-center gap-2 mt-3 text-sm text-dark">
        <input type="checkbox" checked={toutes} onChange={(e) => setToutes(e.target.checked)} className="w-4 h-4 accent-primary" />
        Aussi les positions déjà relevées
      </label>

      <ListeMissions chargement={isLoading} erreur={isError}
        vide={toutes || q ? "Aucune annonce vérifiée ne correspond." : "Toutes les annonces vérifiées ont une position relevée par un agent."}>
        {data?.results.map((a) => (
          <article key={a.id} className="bg-surface rounded-2xl border border-gray-100 shadow-xs p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <h2 className="font-semibold text-dark truncate">{a.name}</h2>
                <p className="text-sm text-gray-500 truncate">{a.type_libelle} · {a.location ? `${a.location}, ` : ""}{a.city}</p>
                {a.hote && <p className="text-xs text-gray-500 mt-0.5">Hôte : {a.hote.nom}</p>}
                <p className={cn("mt-1.5 inline-flex items-center gap-1 text-xs font-semibold rounded-full px-2 py-0.5",
                  a.position_relevee_le ? "bg-green-50 text-green-700" : "bg-amber-50 text-amber-800")}>
                  {a.position_relevee_le
                    ? <><CheckCircle2 size={13} aria-hidden /> Relevée le {formatDate(a.position_relevee_le)}</>
                    : <><MapPin size={13} aria-hidden /> {a.position ? "Point placé par l'hôte" : "Aucun point"}</>}
                </p>
              </div>
              <button type="button" onClick={() => setOuverte(ouverte === a.id ? null : a.id)} aria-expanded={ouverte === a.id}
                className="shrink-0 px-3 py-2 rounded-xl bg-primary text-white text-xs sm:text-sm font-bold">
                {ouverte === a.id ? "Fermer" : "Corriger"}
              </button>
            </div>
            {a.position && (
              <a href={lienCarte(a.position)} target="_blank" rel="noopener noreferrer"
                className="mt-2 inline-flex items-center gap-1 text-xs font-bold text-brand hover:underline">
                Point actuel sur Google Maps <ExternalLink size={12} aria-hidden />
              </a>
            )}
            {ouverte === a.id && <CorrectionPosition annonce={a} onTerminee={() => setOuverte(null)} />}
          </article>
        ))}
      </ListeMissions>
    </div>
  );
}
