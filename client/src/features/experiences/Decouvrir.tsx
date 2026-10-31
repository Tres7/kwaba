"use client";

import { useMemo, useState } from "react";
import { Link } from "@/i18n/navigation";
import { Compass, MapPin, Search, ArrowRight } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import PageHero from "@/components/layout/PageHero";
import { cn } from "@/lib/utils";
import Select from "@/components/ui/Select";
import { useFormat } from "@/lib/format";
import { useExperiences } from "./hooks";
import type { CategorieExperience, Experience } from "./types";

type Category = CategorieExperience;

const TABS: { id: Category | "tout"; label: string }[] = [
  { id: "tout", label: "tout" },
  { id: "activites", label: "activites" },
  { id: "restaurants", label: "restaurants" },
  { id: "loisirs", label: "loisirs" },
  { id: "sites", label: "sites" },
];

/** Texts in the visitor's language; an empty English text falls back to French. */
function localiser(e: Experience, locale: string) {
  const en = locale === "en";
  return {
    ...e,
    nom: (en && e.nom_en) || e.nom,
    etiquette: (en && e.etiquette_en) || e.etiquette,
    pays: (en && e.pays_en) || e.pays,
    description: (en && e.description_en) || e.description,
  };
}

export default function DecouvrirPage() {
  const { formatPrice } = useFormat();
  const t = useTranslations("decouvrir");
  const tNav = useTranslations("nav");
  const locale = useLocale();
  const [tab, setTab] = useState<Category | "tout">("tout");
  const [city, setCity] = useState("");
  const [q, setQ] = useState("");
  const { data: experiences, isLoading } = useExperiences();
  const cities = useMemo(() => Array.from(new Set((experiences ?? []).map((e) => e.ville))).sort((a, b) => a.localeCompare(b, locale)), [experiences, locale]);

  const filtered = useMemo(() => {
    const term = q.trim().toLowerCase();
    return (experiences ?? []).map((e) => localiser(e, locale)).filter(
      (e) =>
        (tab === "tout" || e.categorie === tab) &&
        (!city || e.ville === city) &&
        (!term || `${e.nom} ${e.description} ${e.etiquette} ${e.ville}`.toLowerCase().includes(term))
    );
  }, [experiences, tab, city, q, locale]);

  return (
    <div className="min-h-screen bg-light">
      <PageHero large surtitre={<><Compass size={16} /> {tNav("experiences")}</>} titre={t("titre")} sousTitre={t("sousTitre")} />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 md:py-8">
        <div className="mb-6 md:mb-8">

          <div className="flex gap-6 overflow-x-auto scrollbar-hide border-b border-gray-200 -mx-4 px-4 sm:mx-0 sm:px-0" role="tablist">
            {TABS.map((o) => (
              <button
                key={o.id}
                role="tab"
                aria-selected={tab === o.id}
                onClick={() => setTab(o.id)}
                className={cn(
                  "relative zone-tactile pb-3 text-[15px] font-bold transition-colors whitespace-nowrap border-b-2",
                  tab === o.id ? "text-primary border-primary" : "text-gray-400 border-transparent hover:text-dark"
                )}
              >
                {t(`onglets.${o.label}`)}
              </button>
            ))}
          </div>
        </div>

        <div className="flex flex-col sm:flex-row gap-3 mb-8 bg-white p-3 sm:p-4 rounded-2xl shadow-sm border border-gray-100">
          <Select
            label={t("ville")} value={city} onChange={setCity} className="sm:w-56"
            icon={<MapPin size={16} className="text-primary flex-shrink-0" />}
            options={[{ value: "", label: t("toutesVilles") }, ...cities.map((c) => ({ value: c, label: c }))]}
          />
          <div className="relative flex-1">
            <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="search"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder={t("rechercher")}
              className="w-full h-full min-h-[48px] bg-gray-50 border border-gray-200 rounded-xl pl-12 pr-4 text-base sm:text-sm text-dark outline-none focus:border-primary/50"
            />
          </div>
        </div>

        {isLoading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6" aria-busy="true">
            {[0, 1, 2].map((i) => <div key={i} className="aspect-[4/5] rounded-3xl skeleton" />)}
          </div>
        ) : filtered.length === 0 ? (
          <div className="bg-white rounded-3xl p-12 text-center text-gray-500">
            {t("aucune")}
            <button onClick={() => { setTab("tout"); setCity(""); setQ(""); }} className="block mx-auto mt-3 text-primary font-bold hover:underline">
              {t("reinitialiser")}
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {filtered.map((e) => (
              <article key={e.id} className="bg-white rounded-3xl overflow-hidden shadow-sm border border-gray-100 flex flex-col">
                <div className="relative aspect-[4/3] overflow-hidden bg-slate-100">
                  {e.image && <img src={e.image} alt={e.nom} loading="lazy" className="w-full h-full object-cover" />}
                  <span className="absolute top-4 left-4 px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider rounded-full text-white bg-primary shadow-sm">{e.etiquette}</span>
                </div>
                <div className="p-5 flex flex-col flex-1">
                  <h2 className="font-heading font-bold text-dark text-base leading-tight">{e.nom}</h2>
                  <p className="flex items-center gap-1 text-gray-500 text-sm mt-1"><MapPin size={13} className="text-primary" />{e.ville}, {e.pays}</p>
                  <p className="text-gray-600 text-sm mt-3 leading-relaxed flex-1">{e.description}</p>
                  <div className="flex items-center justify-between mt-4 pt-4 border-t border-gray-100">
                    <span className="font-bold text-primary text-sm">{e.gratuit ? t("gratuit") : e.prix !== null ? `≈ ${formatPrice(e.prix)}` : ""}</span>
                    <Link href={`/recherche?city=${encodeURIComponent(e.ville)}`} className="relative zone-tactile flex items-center gap-1 text-sm font-semibold text-dark hover:text-primary">
                      {t("dormirA", { ville: e.ville })} <ArrowRight size={14} />
                    </Link>
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
