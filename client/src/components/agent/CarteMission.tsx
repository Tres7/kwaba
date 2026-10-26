import Link from "next/link";
import { CheckCircle2, ChevronRight, Home, IdCard, MapPin, UserRound, XCircle } from "lucide-react";
import { urlMission, type MissionResume, type TypeMission } from "@/lib/agent";
import { cn, formatDate } from "@/lib/utils";

const ICONES: Record<TypeMission, typeof Home> = { logement: Home, piece: IdCard };

/** A mission in a list: opens its page (except in the history, where it is closed). */
export default function CarteMission({ mission, action, historique }: {
  mission: MissionResume;
  /** Button on the right ("I'll handle it"). */
  action?: React.ReactNode;
  historique?: boolean;
}) {
  const Icone = ICONES[mission.type] ?? Home;
  const etat = mission.mission;
  const contenu = (
    <>
      {mission.photo ? (
        <img src={mission.photo} alt="" className="w-16 h-16 rounded-xl object-cover bg-gray-100 flex-shrink-0" />
      ) : (
        <span className="w-16 h-16 rounded-xl bg-primary/10 text-primary flex items-center justify-center flex-shrink-0"><Icone size={26} aria-hidden /></span>
      )}
      <span className="flex-1 min-w-0">
        <span className="block text-[11px] font-bold uppercase tracking-wide text-gray-500">{mission.type_libelle}</span>
        <span className="block font-heading font-bold text-dark truncate">{mission.titre}</span>
        {mission.sous_titre && <span className="block text-sm text-gray-500 truncate">{mission.sous_titre}</span>}
        <span className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-gray-500 mt-1">
          {mission.ville && <span className="flex items-center gap-1"><MapPin size={12} aria-hidden /> {mission.ville}</span>}
          <span>{historique ? "Le " : ""}{formatDate(mission.date)}</span>
          {mission.etiquette && !historique && <span className="text-gray-400">{mission.etiquette}</span>}
        </span>
        {etat && <Etat etat={etat} historique={historique} />}
      </span>
    </>
  );

  return (
    <article className="bg-white rounded-2xl border border-gray-100 shadow-sm">
      <div className="flex items-center gap-3 p-3 sm:p-4">
        {historique ? (
          <div className="flex-1 min-w-0 flex items-center gap-3">{contenu}</div>
        ) : (
          <Link href={urlMission(mission.type, mission.cible)} className="flex-1 min-w-0 flex items-center gap-3 rounded-xl">
            {contenu}
            {!action && <ChevronRight size={20} className="text-gray-300 flex-shrink-0" aria-hidden />}
          </Link>
        )}
        {action}
      </div>
    </article>
  );
}

function Etat({ etat, historique }: { etat: NonNullable<MissionResume["mission"]>; historique?: boolean }) {
  if (historique) {
    const validee = etat.decision === "validee";
    return (
      <span className={cn("inline-flex items-center gap-1 mt-1.5 text-xs font-bold rounded-full px-2 py-0.5",
        validee ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700")}>
        {validee ? <CheckCircle2 size={12} aria-hidden /> : <XCircle size={12} aria-hidden />}
        {validee ? "Validé" : "Refusé"}{etat.agent && !etat.moi ? ` · ${etat.agent.nom}` : ""}
      </span>
    );
  }
  return (
    <span className={cn("inline-flex items-center gap-1 mt-1.5 text-xs font-bold rounded-full px-2 py-0.5",
      etat.moi ? "bg-primary/10 text-primary" : "bg-amber-50 text-amber-800")}>
      <UserRound size={12} aria-hidden /> {etat.moi ? "Vous vous en occupez" : `Pris par ${etat.agent?.nom ?? "un agent"}`}
    </span>
  );
}
