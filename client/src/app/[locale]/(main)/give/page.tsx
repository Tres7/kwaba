"use client";

import { useState } from "react";
import { Link } from "@/i18n/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, BadgeCheck, BadgePercent, CalendarClock, FileCheck2, HandHeart } from "lucide-react";
import api from "@/lib/api";
import { CAUSES, useConfigGive } from "@/lib/give";
import { cn } from "@/lib/utils";
import CarteOrganisation from "@/components/give/CarteOrganisation";
import ChiffresImpact from "@/components/give/ChiffresImpact";
import type { CodeCause, ImpactGlobal, Organisation } from "@/types/api/give";
import { useTranslations } from "next-intl";
import PageHero from "@/components/layout/PageHero";

const ENGAGEMENTS = [
  { icon: BadgeCheck, id: "verifiees" },
  { icon: BadgePercent, id: "commission" },
  { icon: CalendarClock, id: "mensuel" },
  // Published transfer proof (not Lucide's "receipt" icon, which shows a $)
  { icon: FileCheck2, id: "preuves" },
];

export default function GivePage() {
  const t = useTranslations("givePage");
  const [cause, setCause] = useState<CodeCause | null>(null);
  const { data: config } = useConfigGive();

  const { data: organisations, isLoading } = useQuery({
    queryKey: ["give", "organisations", cause],
    queryFn: async () =>
      (await api.get<{ results: Organisation[] }>("/v1/give/organisations/", { params: cause ? { cause } : {} })).data.results,
  });
  const { data: impact } = useQuery({
    queryKey: ["give", "impact"],
    queryFn: async () => (await api.get<ImpactGlobal>("/v1/give/impact/")).data,
  });

  return (
    <div className="bg-light pb-12">
      <PageHero surtitre={<><HandHeart size={16} /> Kwa-Ba Give</>} titre={t("titre")} sousTitre={t("sousTitre")}>
          <a href="#organisations" className="mt-6 inline-flex items-center gap-2 bg-secondary text-white font-bold px-6 py-3 rounded-xl hover:bg-secondary/90">
            {t("choisirOng")} <ArrowRight size={18} />
          </a>
          {impact && impact.nb_dons > 0 && <div className="mt-8"><ChiffresImpact impact={impact} clair /></div>}
      </PageHero>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8 space-y-10">
        <section aria-labelledby="causes-titre">
          <h2 id="causes-titre" className="font-heading font-bold text-dark text-xl mb-4">{t("causes")}</h2>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            {(config?.causes ?? []).map((c) => {
              const { icon: Icon, couleur } = CAUSES[c.code];
              const actif = cause === c.code;
              return (
                <button key={c.code} type="button" aria-pressed={actif} onClick={() => setCause(actif ? null : c.code)}
                  className={cn("text-left bg-white rounded-2xl border-2 p-4 transition-colors",
                    actif ? "border-primary" : "border-transparent hover:border-primary/30")}>
                  <span className={cn("inline-flex w-10 h-10 rounded-xl items-center justify-center", couleur)}><Icon size={20} /></span>
                  <p className="font-heading font-bold text-dark mt-3">{CAUSES[c.code].nom}</p>
                  <p className="text-xs text-gray-600 mt-1">{CAUSES[c.code].description}</p>
                </button>
              );
            })}
          </div>
        </section>

        <section id="organisations" aria-labelledby="ong-titre" className="scroll-mt-24">
          <div className="flex flex-wrap items-end justify-between gap-2 mb-4">
            <h2 id="ong-titre" className="font-heading font-bold text-dark text-xl">
              {cause ? `${t("ongPartenaires")} · ${CAUSES[cause].nom}` : t("ongPartenaires")}
            </h2>
            {cause && <button onClick={() => setCause(null)} className="text-sm font-bold text-primary hover:underline">{t("toutesCauses")}</button>}
          </div>
          {isLoading ? (
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">{[0, 1, 2].map((i) => <div key={i} className="h-72 skeleton rounded-3xl" />)}</div>
          ) : !organisations?.length ? (
            <p className="bg-white rounded-2xl border border-gray-100 p-8 text-center text-gray-600">
              {cause ? t("aucuneOngCause") : t("aucuneOng")}
            </p>
          ) : (
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {organisations.map((o) => <CarteOrganisation key={o.id} o={o} />)}
            </div>
          )}
        </section>

        <section aria-labelledby="engagements-titre">
          <h2 id="engagements-titre" className="font-heading font-bold text-dark text-xl mb-4">{t("engagements")}</h2>
          <ul className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {ENGAGEMENTS.map(({ icon: Icon, id }) => (
              <li key={id} className="bg-white rounded-2xl border border-gray-100 p-5">
                {/* Same badge as the causes: a single icon family on the page */}
                <span className="inline-flex w-10 h-10 rounded-xl items-center justify-center bg-primary/10 text-primary"><Icon size={20} /></span>
                <p className="font-heading font-bold text-dark mt-3">{t(`engagementsListe.${id}.titre`)}</p>
                <p className="text-sm text-gray-600 mt-1">{t(`engagementsListe.${id}.texte`)}</p>
              </li>
            ))}
          </ul>
          <Link href="/give/impact" className="inline-flex items-center gap-1.5 mt-4 text-sm font-bold text-primary hover:underline">
            {t("voirImpact")} <ArrowRight size={15} />
          </Link>
        </section>
      </div>
    </div>
  );
}
