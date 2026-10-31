"use client";

import { useState } from "react";
import { useTableauAgent, useMissions } from "../hooks";
import CarteMission from "./CarteMission";
import ListeMissions from "./ListeMissions";

/** Finished checks: mine (an administrator also sees those of the whole team). */
export default function HistoriquePage() {
  const { data: tableau } = useTableauAgent();
  const [miennes, setMiennes] = useState(false);
  const admin = !!tableau?.admin;
  const { data, isLoading, isError } = useMissions("historique", { agent: admin && miennes ? "moi" : "" });

  return (
    <div>
      <h1 className="font-heading font-bold text-2xl text-dark">Historique</h1>
      <p className="text-sm text-gray-500 mt-1">
        {admin ? "Les contrôles terminés par toute l'équipe, les plus récents d'abord." : "Vos contrôles terminés, les plus récents d'abord."}
      </p>

      {admin && (
        <label className="inline-flex items-center gap-2 mt-4 text-sm text-dark">
          <input type="checkbox" checked={miennes} onChange={(e) => setMiennes(e.target.checked)} className="w-4 h-4 accent-primary" />
          Seulement les miens
        </label>
      )}

      <ListeMissions chargement={isLoading} erreur={isError} vide="Aucun contrôle terminé pour le moment.">
        {data?.results.map((m) => <CarteMission key={m.mission?.id ?? `${m.type}-${m.cible}`} mission={m} historique />)}
      </ListeMissions>
    </div>
  );
}
