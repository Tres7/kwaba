"use client";

import { useState } from "react";
import { useMissions } from "@/lib/agent";
import CarteMission from "@/components/agent/CarteMission";
import ListeMissions from "@/components/agent/ListeMissions";

/** Ongoing missions: mine, or those of the other agents (to know who does what). */
export default function MesMissionsPage() {
  const [vue, setVue] = useState<"miennes" | "equipe">("miennes");
  const { data, isLoading, isError } = useMissions(vue);

  return (
    <div>
      <h1 className="font-heading font-bold text-2xl text-dark">Mes missions</h1>
      <p className="text-sm text-gray-500 mt-1">Les contrôles dont vous vous occupez. Relâchez une mission depuis sa fiche si vous ne pouvez pas la faire.</p>

      <div className="inline-flex bg-white border border-gray-200 rounded-xl p-1 mt-5" role="tablist" aria-label="Missions en cours">
        {([["miennes", "Les miennes"], ["equipe", "L'équipe"]] as const).map(([code, libelle]) => (
          <button key={code} type="button" role="tab" aria-selected={vue === code} onClick={() => setVue(code)}
            className={vue === code ? "px-4 py-2 rounded-lg bg-primary text-white text-sm font-bold" : "px-4 py-2 rounded-lg text-sm font-semibold text-dark"}>
            {libelle}
          </button>
        ))}
      </div>

      <ListeMissions chargement={isLoading} erreur={isError}
        vide={vue === "miennes" ? "Aucune mission en cours. Prenez-en une dans « À faire »." : "Aucun autre agent n'a de mission en cours."}>
        {data?.results.map((m) => <CarteMission key={`${m.type}-${m.cible}`} mission={m} />)}
      </ListeMissions>
    </div>
  );
}
