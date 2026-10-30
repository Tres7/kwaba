"use client";

import { Link } from "@/i18n/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import api from "@/lib/api";
import { useTextesGive } from "@/lib/give";
import { cn } from "@/lib/utils";
import ChiffresImpact from "@/components/give/ChiffresImpact";
import PreuveReversement from "@/components/give/PreuveReversement";
import type { ImpactGlobal } from "@/types/api/give";
import { useTranslations } from "next-intl";
import { useFormat } from "@/lib/format";

export default function ImpactPage() {
  const { CAUSES } = useTextesGive();
  const { formatPrice } = useFormat();
  const t = useTranslations("impactPage");
  const tG = useTranslations("give");
  const { data: impact, isLoading } = useQuery({
    queryKey: ["give", "impact"],
    queryFn: async () => (await api.get<ImpactGlobal>("/v1/give/impact/")).data,
  });

  return (
    <div className="bg-light pb-12">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8 sm:py-12 space-y-8">
        <div>
          <Link href="/give" className="inline-flex items-center gap-1.5 text-sm font-bold text-primary hover:underline"><ArrowLeft size={15} /> Kwa-Ba Give</Link>
          <h1 className="font-heading font-bold text-dark text-2xl sm:text-3xl mt-3">{t("titre")}</h1>
          <p className="text-gray-600 mt-2 max-w-2xl">
            {t("texte")}
          </p>
        </div>

        {isLoading || !impact ? (
          <div className="h-24 skeleton rounded-2xl" />
        ) : (
          <>
            <ChiffresImpact impact={impact} />

            <section aria-labelledby="causes-titre">
              <h2 id="causes-titre" className="font-heading font-bold text-dark text-xl mb-3">{t("parCause")}</h2>
              <ul className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {impact.causes.map((c) => {
                  const { icon: Icon, couleur } = CAUSES[c.code];
                  return (
                    <li key={c.code} className="bg-white rounded-2xl border border-gray-100 p-4">
                      <span className={cn("inline-flex w-9 h-9 rounded-xl items-center justify-center", couleur)}><Icon size={18} /></span>
                      <p className="font-bold text-dark text-sm mt-2">{CAUSES[c.code].nom}</p>
                      <p className="text-xs text-gray-600 mt-0.5">{formatPrice(c.collecte)} · {tG("nbDons", { nombre: c.nb_dons })}</p>
                    </li>
                  );
                })}
              </ul>
            </section>

            <section aria-labelledby="preuves-titre">
              <h2 id="preuves-titre" className="font-heading font-bold text-dark text-xl mb-3">{t("derniers")}</h2>
              {impact.reversements.length === 0 ? (
                <p className="bg-white rounded-2xl border border-gray-100 p-5 text-sm text-gray-600">
                  {t("aucun")}
                </p>
              ) : (
                <ul className="space-y-2">{impact.reversements.map((r) => <PreuveReversement key={r.id} r={r} avecOrganisation />)}</ul>
              )}
            </section>
          </>
        )}
      </div>
    </div>
  );
}
