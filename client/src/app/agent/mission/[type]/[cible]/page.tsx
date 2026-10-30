"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ArrowLeft, Hand, Undo2, UserRound } from "lucide-react";
import api, { apiErrorMessage, estErreurApi } from "@/lib/api";
import type { MissionEtat, TypeMission } from "@/lib/agent";
import { formatDate } from "@/lib/utils";
import FicheLogement, { type Logement } from "@/components/agent/FicheLogement";
import FichePiece, { type Piece } from "@/components/agent/FichePiece";

interface Fiche {
  type: TypeMission;
  type_libelle: string;
  cible: string;
  titre: string;
  sous_titre: string;
  ville: string;
  mission: MissionEtat | null;
  droits: { prendre: boolean; liberer: boolean; decider: boolean };
  // Depending on the type
  logement?: Logement;
  controles?: Record<string, string>;
  max_photos?: number;
  piece?: Piece;
}

/** Page of a mission: who handles it, then the check itself (depending on the type). */
export default function FicheMissionPage() {
  const { type, cible } = useParams<{ type: string; cible: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [action, setAction] = useState(false);
  const cle = ["agent", "mission", type, cible];

  const { data, isLoading, error } = useQuery({
    queryKey: cle,
    queryFn: async () => (await api.get<Fiche>(`/v1/agent/missions/${type}/${cible}/`)).data,
    retry: false,
  });

  const agir = async (quoi: "prendre" | "liberer") => {
    if (quoi === "liberer" && !window.confirm("Relâcher cette mission ? Elle revient dans la file commune.")) return;
    setAction(true);
    try {
      await api.post(`/v1/agent/missions/${type}/${cible}/${quoi}/`);
      toast.success(quoi === "prendre" ? "Mission prise : elle est à vous." : "Mission relâchée.");
      await queryClient.invalidateQueries({ queryKey: ["agent"] });
      if (quoi === "liberer") router.push("/agent/a-faire");
    } catch (err) {
      toast.error(apiErrorMessage(err));
      await queryClient.invalidateQueries({ queryKey: ["agent"] });
    } finally {
      setAction(false);
    }
  };

  const terminee = async (message: string) => {
    toast.success(message);
    await queryClient.invalidateQueries({ queryKey: ["agent"] });
    await queryClient.invalidateQueries({ queryKey: ["verification", "compteurs"] });
    router.push("/agent/missions");
  };

  if (isLoading) return <div className="space-y-3">{[0, 1, 2].map((i) => <div key={i} className="h-28 skeleton rounded-2xl" />)}</div>;

  if (error || !data) {
    const introuvable = estErreurApi(error) && error.response?.status === 404;
    return (
      <div className="bg-white rounded-2xl border border-gray-100 p-8 text-center">
        <p className="font-heading font-bold text-dark">{introuvable ? "Cette mission n'est plus à faire" : "Impossible d'ouvrir cette mission"}</p>
        <p className="text-sm text-gray-500 mt-1">{introuvable ? "Elle a été traitée ou retirée entre-temps." : apiErrorMessage(error)}</p>
        <Link href="/agent/a-faire" className="inline-block mt-4 text-primary font-bold hover:underline">Voir les missions à faire</Link>
      </div>
    );
  }

  const { mission, droits } = data;

  return (
    <div>
      <button type="button" onClick={() => router.back()} className="flex items-center gap-1.5 text-sm font-semibold text-gray-500 hover:text-primary">
        <ArrowLeft size={16} aria-hidden /> Retour
      </button>
      <p className="text-[11px] font-bold uppercase tracking-wide text-gray-500 mt-4">{data.type_libelle}</p>
      <h1 className="font-heading font-bold text-2xl text-dark leading-tight">{data.titre}</h1>
      {(data.sous_titre || data.ville) && (
        <p className="text-sm text-gray-500 mt-1">{[data.sous_titre, data.ville].filter(Boolean).join(" · ")}</p>
      )}

      {/* Who handles it */}
      <div className="mt-5 mb-5 flex flex-wrap items-center justify-between gap-3 rounded-2xl px-4 py-3 bg-white border border-gray-100 shadow-sm">
        <p className="flex items-center gap-2 text-sm text-dark">
          <UserRound size={18} className="text-primary flex-shrink-0" aria-hidden />
          <span>
            {!mission ? "Personne ne s'en occupe pour le moment."
              : mission.moi ? <>Vous vous en occupez depuis le {formatDate(mission.prise_le)}.</>
                : <><strong>{mission.agent?.nom ?? "Un agent"}</strong> s&apos;en occupe depuis le {formatDate(mission.prise_le)}.</>}
          </span>
        </p>
        <div className="flex gap-2">
          {droits.prendre && (
            <button type="button" onClick={() => agir("prendre")} disabled={action}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-primary text-white text-sm font-bold disabled:opacity-60">
              <Hand size={16} aria-hidden /> Je m&apos;en occupe
            </button>
          )}
          {droits.liberer && (
            <button type="button" onClick={() => agir("liberer")} disabled={action}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-gray-200 text-sm font-bold text-dark disabled:opacity-60">
              <Undo2 size={16} aria-hidden /> Relâcher
            </button>
          )}
        </div>
      </div>

      {!droits.decider && (
        <p className="mb-5 text-sm bg-amber-50 text-amber-900 rounded-2xl px-4 py-3">
          Lecture seule : seul l&apos;agent qui s&apos;en occupe (ou un administrateur) peut décider.
        </p>
      )}

      {data.type === "logement" && data.logement && (
        <FicheLogement logement={data.logement} controlesLibelles={data.controles ?? {}} maxPhotos={data.max_photos ?? 10}
          peutDecider={droits.decider} onTerminee={terminee} />
      )}
      {data.type === "piece" && data.piece && (
        <FichePiece piece={data.piece} peutDecider={droits.decider} onTerminee={terminee} />
      )}
    </div>
  );
}
