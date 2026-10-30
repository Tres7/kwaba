"use client";

import { Suspense, useState } from "react";
import { Link } from "@/i18n/navigation";
import { useParams, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, BadgeCheck, ExternalLink, MapPin } from "lucide-react";
import api from "@/lib/api";
import { CAUSES, PAYS } from "@/lib/give";
import { cn, formatDate, formatPrice } from "@/lib/utils";
import { urlExterneSure } from "@/lib/url-sure";
import ChiffresImpact from "@/components/give/ChiffresImpact";
import FormulaireDon from "@/components/give/FormulaireDon";
import PreuveReversement from "@/components/give/PreuveReversement";
import type { OrganisationDetail } from "@/types/api/give";
import { useTranslations } from "next-intl";

function PageOrganisation() {
  const t = useTranslations("ongPage");
  const tG = useTranslations("give");
  const { slug } = useParams<{ slug: string }>();
  const searchParams = useSearchParams();
  const [projetId, setProjetId] = useState<string | null>(searchParams.get("projet"));

  const { data: o, isError } = useQuery({
    queryKey: ["give", "organisation", slug],
    queryFn: async () => (await api.get<OrganisationDetail>(`/v1/give/organisations/${slug}/`)).data,
    retry: false,
  });

  if (isError) {
    return (
      <div className="min-h-[50vh] flex flex-col items-center justify-center gap-3 text-center px-6">
        <p className="font-heading font-bold text-xl text-dark">{t("introuvable")}</p>
        <Link href="/give" className="text-primary font-bold hover:underline">{t("voirOng")}</Link>
      </div>
    );
  }
  if (!o) return <div className="max-w-6xl mx-auto px-4 py-10"><div className="h-96 skeleton rounded-3xl" /></div>;

  const cause = CAUSES[o.cause];
  const choisir = (id: string | null) => {
    setProjetId(id);
    document.getElementById("don")?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <div className="bg-light pb-12">
      <div className="relative h-48 sm:h-64 bg-primary-800">
        {o.image && (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={o.image} alt="" className="w-full h-full object-cover opacity-80" />
        )}
        <Link href="/give" className="absolute top-4 left-4 flex items-center gap-1.5 bg-white/90 text-dark text-sm font-bold px-3 py-1.5 rounded-full">
          <ArrowLeft size={15} /> Kwa-Ba Give
        </Link>
      </div>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 -mt-10 relative grid lg:grid-cols-[1fr_24rem] gap-6 items-start">
        <div className="space-y-6 min-w-0">
          <section className="bg-white rounded-3xl border border-gray-100 p-5 sm:p-6">
            <div className="flex items-start gap-4">
              {o.logo && (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={o.logo} alt="" className="w-16 h-16 rounded-2xl object-cover border border-gray-100 flex-shrink-0" />
              )}
              <div className="min-w-0">
                <span className={cn("inline-flex items-center gap-1 text-xs font-bold px-2.5 py-1 rounded-full", cause.couleur)}>
                  <cause.icon size={12} /> {cause.nom}
                </span>
                <h1 className="font-heading font-bold text-dark text-2xl sm:text-3xl mt-2">{o.nom}</h1>
                <p className="flex items-center gap-1 text-sm text-gray-600 mt-1"><MapPin size={14} /> {o.ville}, {PAYS[o.pays] ?? o.pays}</p>
              </div>
            </div>
            <p className="text-dark mt-4 whitespace-pre-line">{o.description}</p>
            {urlExterneSure(o.site_web) && (
              <a href={urlExterneSure(o.site_web)} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1.5 mt-3 text-sm font-bold text-primary hover:underline">
                {t("site")} <ExternalLink size={14} /><span className="sr-only"> ({tG("nouvelOnglet")})</span>
              </a>
            )}
          </section>

          <section aria-labelledby="verif-titre" className="bg-white rounded-3xl border-2 border-primary/20 p-5 sm:p-6">
            <h2 id="verif-titre" className="flex items-center gap-2 font-heading font-bold text-dark text-lg">
              <BadgeCheck size={20} className="text-primary" /> {t("verifieeLe", { date: formatDate(o.verifiee_le, { day: "numeric", month: "long", year: "numeric" }) })}
            </h2>
            <p className="text-sm text-gray-600 mt-2">{t("enregistrement")} <span className="font-mono text-dark">{o.numero_enregistrement}</span></p>
            {o.verification && <p className="text-sm text-dark mt-2 whitespace-pre-line">{o.verification}</p>}
          </section>

          <section aria-labelledby="impact-titre">
            <h2 id="impact-titre" className="font-heading font-bold text-dark text-xl mb-3">{t("impact")}</h2>
            <ChiffresImpact impact={o.impact} />
          </section>

          {o.projets.length > 0 && (
            <section aria-labelledby="projets-titre">
              <h2 id="projets-titre" className="font-heading font-bold text-dark text-xl mb-3">{t("projets")}</h2>
              <ul className="grid sm:grid-cols-2 gap-4">
                {o.projets.map((p) => {
                  const pourcentage = p.objectif ? Math.min(100, Math.round((p.collecte / p.objectif) * 100)) : null;
                  return (
                    <li key={p.id} className={cn("bg-white rounded-2xl border-2 overflow-hidden flex flex-col", projetId === p.id ? "border-primary" : "border-gray-100")}>
                      {p.image && (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img src={p.image} alt="" className="w-full h-32 object-cover" />
                      )}
                      <div className="p-4 flex-1 flex flex-col">
                        <p className="font-heading font-bold text-dark">{p.titre}</p>
                        {p.lieu && <p className="text-xs text-gray-600 mt-0.5">{p.lieu}</p>}
                        <p className="text-sm text-gray-600 mt-2 flex-1">{p.resume}</p>
                        {pourcentage !== null && (
                          <div className="mt-3">
                            <div className="h-2 rounded-full bg-gray-100 overflow-hidden" role="progressbar" aria-valuenow={pourcentage} aria-valuemin={0} aria-valuemax={100}
                              aria-label={t("objectifAtteint", { pourcentage })}>
                              <div className="h-full bg-secondary" style={{ width: `${pourcentage}%` }} />
                            </div>
                            <p className="text-xs text-gray-600 mt-1">{t("sur", { collecte: formatPrice(p.collecte), objectif: formatPrice(p.objectif ?? 0) })}</p>
                          </div>
                        )}
                        <button type="button" onClick={() => choisir(projetId === p.id ? null : p.id)}
                          className="mt-3 text-sm font-bold text-primary text-left hover:underline">
                          {projetId === p.id ? t("donnerGeneral") : t("soutenirProjet")}
                        </button>
                      </div>
                    </li>
                  );
                })}
              </ul>
            </section>
          )}

          <section id="reversements" aria-labelledby="reversements-titre" className="scroll-mt-24">
            <h2 id="reversements-titre" className="font-heading font-bold text-dark text-xl mb-3">{t("reversements")}</h2>
            {o.reversements.length === 0 ? (
              <p className="bg-white rounded-2xl border border-gray-100 p-5 text-sm text-gray-600">
                {t("aucunReversement")}
              </p>
            ) : (
              <ul className="space-y-2">{o.reversements.map((r) => <PreuveReversement key={r.id} r={r} />)}</ul>
            )}
          </section>
        </div>

        <div className="lg:sticky lg:top-24">
          <FormulaireDon organisation={o} projetId={projetId} />
        </div>
      </div>
    </div>
  );
}

export default function Page() {
  return (
    <Suspense>
      <PageOrganisation />
    </Suspense>
  );
}
