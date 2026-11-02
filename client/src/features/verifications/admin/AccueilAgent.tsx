"use client";

import Link from "next/link";
import { useSession } from "next-auth/react";
import { ArrowRight, CheckCircle2, ClipboardList, Home, IdCard, UserCheck } from "lucide-react";
import { useTableauAgent, type TypeMission } from "../hooks";

const ICONES: Record<TypeMission, typeof Home> = { logement: Home, piece: IdCard };

/** Home of the agent space: what waits in the shared queue, my ongoing missions, my activity this month. */
export default function AccueilAgentPage() {
  const { data: session } = useSession();
  const { data, isLoading, isError } = useTableauAgent();
  const prenom = session?.user?.name?.split(" ")[0];
  const libres = data?.types.reduce((n, t) => n + t.libres, 0) ?? 0;
  const miennes = data?.types.reduce((n, t) => n + t.miennes, 0) ?? 0;

  return (
    <div>
      <h1 className="font-heading font-bold text-2xl text-dark">Bonjour{prenom ? ` ${prenom}` : ""}</h1>
      <p className="text-sm text-gray-500 mt-1">
        Prenez une mission dans la file commune : elle n&apos;est plus proposée aux autres agents tant que vous vous en occupez.
      </p>

      {isError ? (
        <p className="mt-6 bg-red-50 text-red-700 rounded-2xl p-4 text-sm">Accès réservé aux agents de terrain.</p>
      ) : (
        <>
          <div className="grid grid-cols-3 gap-3 mt-6">
            <Chiffre href="/agent/a-faire" icone={ClipboardList} valeur={libres} libelle="À faire" chargement={isLoading} accent />
            <Chiffre href="/agent/missions" icone={UserCheck} valeur={miennes} libelle="Mes missions" chargement={isLoading} />
            <Chiffre href="/agent/historique" icone={CheckCircle2} valeur={data?.faites_ce_mois ?? 0} libelle="Faites ce mois" chargement={isLoading} />
          </div>

          <h2 className="font-heading font-bold text-lg text-dark mt-8">Par type de mission</h2>
          <div className="mt-3 space-y-3">
            {isLoading
              ? [0, 1].map((i) => <div key={i} className="h-20 skeleton rounded-2xl" />)
              : data?.types.map((t) => {
                const Icone = ICONES[t.type] ?? Home;
                return (
                  <Link key={t.type} href={`/agent/a-faire?type=${t.type}`}
                    className="flex items-center gap-3 bg-white rounded-2xl border border-gray-100 shadow-sm p-4 hover:border-primary/30">
                    <span className="w-12 h-12 rounded-xl bg-primary/10 text-primary flex items-center justify-center flex-shrink-0"><Icone size={22} aria-hidden /></span>
                    <span className="flex-1 min-w-0">
                      <span className="block font-heading font-bold text-dark">{t.libelle}</span>
                      <span className="block text-sm text-gray-500">
                        {t.libres} à prendre{t.miennes ? ` · ${t.miennes} à vous` : ""}{t.equipe ? ` · ${t.equipe} pris par l'équipe` : ""}
                      </span>
                    </span>
                    <ArrowRight size={18} className="text-gray-300 flex-shrink-0" aria-hidden />
                  </Link>
                );
              })}
          </div>
        </>
      )}
    </div>
  );
}

function Chiffre({ href, icone: Icone, valeur, libelle, chargement, accent }: {
  href: string; icone: typeof Home; valeur: number; libelle: string; chargement: boolean; accent?: boolean;
}) {
  return (
    <Link href={href} className={accent ? "rounded-2xl p-3 sm:p-4 bg-primary text-white" : "rounded-2xl p-3 sm:p-4 bg-white border border-gray-100 shadow-sm text-dark"}>
      <Icone size={18} aria-hidden className={accent ? "text-white/80" : "text-primary"} />
      <span className="block font-heading font-bold text-2xl sm:text-3xl mt-2 tabular-nums">{chargement ? "–" : valeur}</span>
      <span className={accent ? "block text-xs sm:text-sm text-white/80" : "block text-xs sm:text-sm text-gray-500"}>{libelle}</span>
    </Link>
  );
}
