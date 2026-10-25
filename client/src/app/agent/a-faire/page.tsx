"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Hand, Search } from "lucide-react";
import api, { apiErrorMessage } from "@/lib/api";
import { TYPES_MISSION, urlMission, useMissions, type MissionResume, type TypeMission } from "@/lib/agent";
import CarteMission from "@/components/agent/CarteMission";
import ListeMissions from "@/components/agent/ListeMissions";

function Prendre({ mission }: { mission: MissionResume }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [envoi, setEnvoi] = useState(false);

  const prendre = async () => {
    setEnvoi(true);
    try {
      await api.post(`/v1/agent/missions/${mission.type}/${mission.cible}/prendre/`);
      await queryClient.invalidateQueries({ queryKey: ["agent"] });
      router.push(urlMission(mission.type, mission.cible));
    } catch (err) {
      toast.error(apiErrorMessage(err));
      await queryClient.invalidateQueries({ queryKey: ["agent"] });
      setEnvoi(false);
    }
  };

  return (
    <button type="button" onClick={prendre} disabled={envoi}
      className="flex-shrink-0 flex flex-col sm:flex-row items-center gap-1 sm:gap-2 px-3 py-2 rounded-xl bg-primary text-white text-xs sm:text-sm font-bold disabled:opacity-60">
      <Hand size={16} aria-hidden /> {envoi ? "…" : "Je m'en occupe"}
    </button>
  );
}

function AFaire() {
  const params = useSearchParams();
  const initial = params.get("type");
  const [type, setType] = useState<TypeMission | "">(TYPES_MISSION.some((t) => t.code === initial) ? (initial as TypeMission) : "");
  const [q, setQ] = useState("");
  const { data, isLoading, isError } = useMissions("a_faire", { type, q: q.trim() });

  return (
    <div>
      <h1 className="font-heading font-bold text-2xl text-dark">À faire</h1>
      <p className="text-sm text-gray-500 mt-1">La file commune, les plus anciennes d&apos;abord. Une mission prise disparaît de la liste des autres agents.</p>

      <div className="flex gap-2 overflow-x-auto mt-5 pb-1 -mx-4 px-4 sm:mx-0 sm:px-0" role="group" aria-label="Type de mission">
        {[{ code: "" as const, court: "Toutes" }, ...TYPES_MISSION].map((t) => (
          <button key={t.code} type="button" onClick={() => setType(t.code)} aria-pressed={type === t.code}
            className={type === t.code
              ? "flex-shrink-0 px-4 py-2 rounded-full bg-primary text-white text-sm font-bold"
              : "flex-shrink-0 px-4 py-2 rounded-full bg-white border border-gray-200 text-sm font-semibold text-dark"}>
            {t.court}
          </button>
        ))}
      </div>

      <label className="relative block mt-3">
        <span className="sr-only">Rechercher par nom, ville ou adresse</span>
        <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" aria-hidden />
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Nom, ville ou quartier"
          className="w-full pl-11 pr-4 py-3 bg-white border border-gray-200 rounded-xl text-base sm:text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary" />
      </label>

      <ListeMissions chargement={isLoading} erreur={isError} vide="Rien à faire pour le moment : toutes les missions sont prises ou terminées.">
        {data?.results.map((m) => <CarteMission key={`${m.type}-${m.cible}`} mission={m} action={<Prendre mission={m} />} />)}
      </ListeMissions>
    </div>
  );
}

export default function AFairePage() {
  return <Suspense fallback={null}><AFaire /></Suspense>;
}
