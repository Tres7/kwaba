"use client";

import { Link } from "@/i18n/navigation";
import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { QuotesIcon, SealCheckIcon, StarIcon } from "@phosphor-icons/react";
import api from "@/lib/api";
import { initials } from "@/lib/utils";
import type { Avis, AvisPage, Hebergement } from "@/types/api/models";

/** Listings read (best rated first) and reviews shown. */
const LOGEMENTS_LUS = 4;
const AVIS_AFFICHES = 3;
/** A review must say something to be quoted on the home page. */
const LONGUEUR_MIN = 40;

/**
 * Home: a few verified reviews (left after a stay), taken from the best rated listings already loaded by the page,
 * one per listing if possible. Nothing is shown while there are none.
 */
export default function AvisVoyageurs({ hebergements }: { hebergements: Hebergement[] }) {
  const t = useTranslations("accueil.avis");
  const tAvis = useTranslations("avis");
  const sources = hebergements.filter((h) => h.review_count > 0).slice(0, LOGEMENTS_LUS);

  const { data: cites = [] } = useQuery({
    queryKey: ["avis", "accueil", sources.map((h) => h.id)],
    enabled: sources.length > 0,
    staleTime: 10 * 60_000,
    queryFn: async () => {
      const pages = await Promise.all(sources.map(async (h) => {
        const res = await api.get<AvisPage>("/v1/avis/", { params: { hebergement: h.id, limit: 3 } }).catch(() => null);
        const bons = (res?.data.results ?? []).filter((a) => a.note >= 4 && a.commentaire.trim().length >= LONGUEUR_MIN);
        return bons.map((avis) => ({ avis, h }));
      }));
      // One review per listing first, then the following ones
      const choisis: { avis: Avis; h: Hebergement }[] = [];
      for (let rang = 0; choisis.length < AVIS_AFFICHES && pages.some((p) => p[rang]); rang++) {
        for (const p of pages) if (p[rang] && choisis.length < AVIS_AFFICHES) choisis.push(p[rang]);
      }
      return choisis;
    },
  });

  if (cites.length === 0) return null;

  return (
    <section aria-labelledby="avis-titre">
      <div className="mb-6 md:mb-8">
        <h2 id="avis-titre" className="font-heading font-bold text-dark text-2xl md:text-3xl">{t("titre")}</h2>
        <p className="text-gray-500 text-sm mt-1">{t("texte")}</p>
      </div>
      <ul className="grid grid-cols-1 md:grid-cols-3 gap-4 md:gap-6">
        {cites.map(({ avis, h }) => {
          const nom = `${avis.auteur.prenom} ${avis.auteur.initiale}`.trim();
          return (
            <li key={avis.id} className="relative bg-white rounded-2xl border border-gray-100 shadow-sm p-6 flex flex-col">
              <QuotesIcon size={36} weight="fill" className="absolute top-5 right-5 text-primary-100" aria-hidden />
              <p className="flex gap-0.5 text-accent" aria-label={`${avis.note}/5`}>
                {[1, 2, 3, 4, 5].map((n) => <StarIcon key={n} size={16} weight={n <= avis.note ? "fill" : "regular"} aria-hidden />)}
              </p>
              <blockquote className="mt-3 text-dark text-[15px] leading-relaxed line-clamp-5">{avis.commentaire}</blockquote>
              <div className="mt-auto pt-5 flex items-center gap-3">
                <span className="h-10 w-10 rounded-full bg-primary-50 text-primary font-bold text-sm flex items-center justify-center overflow-hidden flex-shrink-0">
                  {avis.auteur.avatar_url ? <img src={avis.auteur.avatar_url} alt="" className="w-full h-full object-cover" /> : initials(nom)}
                </span>
                <span className="min-w-0 text-sm">
                  <span className="block font-semibold text-dark">{nom}</span>
                  <span className="flex items-center gap-1 text-gray-500 min-w-0">
                    <SealCheckIcon size={14} weight="fill" className="text-secondary flex-shrink-0" aria-label={tAvis("sejourVerifie")} />
                    <Link href={`/hebergements/${h.id}`} className="truncate hover:text-primary hover:underline">{h.name}, {h.city}</Link>
                  </span>
                </span>
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
