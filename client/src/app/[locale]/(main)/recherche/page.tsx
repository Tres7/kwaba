"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { usePathname, useRouter } from "@/i18n/navigation";
import { useSession } from "next-auth/react";
import { useQuery } from "@tanstack/react-query";
import { List, Map as IconeCarte, Search, SlidersHorizontal, X } from "lucide-react";
import api from "@/lib/api";
import { cn, formatDate } from "@/lib/utils";
import Chargement from "@/components/ui/Chargement";
import PropertyCard from "@/components/hebergement/PropertyCard";
import { BandeauBientot, useAucunLogement } from "@/components/lancement/BientotDisponible";
import DateRangeField from "@/components/ui/DateRangeField";
import GuestsField from "@/components/ui/GuestsField";
import Select from "@/components/ui/Select";
import type { Hebergement, Paginated } from "@/types/api/models";
import { useTranslations } from "next-intl";
import ChampDestination from "@/components/hebergement/ChampDestination";
import { AMENITIES, EQUIPEMENTS_PRINCIPAUX, estRegle } from "@/components/hebergement/AmenityBadge";
import MapEmbed from "@/components/hebergement/MapEmbed";
import { QUARTIERS_LOME } from "@/lib/quartiers";

const SORTS = [
  { id: "", label: "pertinence" },
  { id: "prix_asc", label: "prixCroissant" },
  { id: "prix_desc", label: "prixDecroissant" },
  { id: "note", label: "meilleuresNotes" },
];

const TYPES = [
  { id: "", label: "tous" },
  { id: "hotel", label: "hotels" },
  { id: "villa", label: "villas" },
  { id: "appartement", label: "appartements" },
  { id: "auberge", label: "auberges" },
  { id: "maison", label: "maisons" },
  { id: "residence", label: "residences" },
];

// Behind « more amenities »: every other amenity, and the house rules a traveller looks for
const REGLES_RECHERCHEES = ["animaux_acceptes", "non_fumeur", "fumeur_autorise", "fetes_autorisees"];
const AUTRES_EQUIPEMENTS = Object.keys(AMENITIES).filter((id) => !EQUIPEMENTS_PRINCIPAUX.includes(id)
  && (!estRegle(id) || REGLES_RECHERCHEES.includes(id)));

const FILTER_KEYS = ["city", "check_in", "check_out", "guests", "type", "sort", "price_min", "price_max", "petit_dejeuner", "equipements", "disponibles"] as const;

function RechercheContent() {
  const t = useTranslations("recherche");
  const aucunLogement = useAucunLogement();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const { status } = useSession();

  // The URL is the source of truth: shareable and works with the back button
  const params = Object.fromEntries(FILTER_KEYS.map((k) => [k, searchParams.get(k) ?? ""])) as Record<(typeof FILTER_KEYS)[number], string>;

  const [city, setCity] = useState(params.city);
  const [checkIn, setCheckIn] = useState(params.check_in);
  const [checkOut, setCheckOut] = useState(params.check_out);
  const [guests, setGuests] = useState(params.guests || "1");
  const [priceMin, setPriceMin] = useState(params.price_min);
  const [priceMax, setPriceMax] = useState(params.price_max);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [carte, setCarte] = useState(false);
  const [tousEquipements, setTousEquipements] = useState(false);

  // Syncs the form again when the URL changes (search from the navbar, back button…)
  useEffect(() => {
    setCity(searchParams.get("city") ?? "");
    setCheckIn(searchParams.get("check_in") ?? "");
    setCheckOut(searchParams.get("check_out") ?? "");
    setGuests(searchParams.get("guests") || "1");
    setPriceMin(searchParams.get("price_min") ?? "");
    setPriceMax(searchParams.get("price_max") ?? "");
  }, [searchParams]);

  const pushParams = (patch: Partial<Record<(typeof FILTER_KEYS)[number], string>>) => {
    const next = new URLSearchParams(searchParams.toString());
    for (const [k, v] of Object.entries(patch)) {
      if (v) next.set(k, v);
      else next.delete(k);
    }
    router.push(`${pathname}?${next.toString()}`, { scroll: false });
  };

  const submitSearch = (e?: React.FormEvent) => {
    e?.preventDefault();
    const validDates = checkIn && checkOut && checkOut > checkIn;
    pushParams({
      city: city.trim(),
      check_in: validDates ? checkIn : "",
      check_out: validDates ? checkOut : "",
      guests: guests === "1" ? "" : guests,
      price_min: priceMin,
      price_max: priceMax,
    });
    setFiltersOpen(false);
  };

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["hebergements", "recherche", searchParams.toString(), status],
    queryFn: async () => {
      const query: Record<string, string> = {};
      for (const k of FILTER_KEYS) if (params[k]) query[k] = params[k];
      return (await api.get<Paginated<Hebergement>>("/v1/hebergements/", { params: query })).data;
    },
    enabled: status !== "loading",
  });

  const results = data?.results ?? [];
  const avecDates = Boolean(params.check_in && params.check_out);
  const nbDisponibles = results.filter((h) => h.disponibilite?.disponible).length;
  const stayQuery = params.check_in && params.check_out
    ? `?check_in=${params.check_in}&check_out=${params.check_out}&guests=${params.guests || 1}`
    : "";
  const equipements = params.equipements ? params.equipements.split(",") : [];
  const basculerEquipement = (id: string) => {
    const suivants = equipements.includes(id) ? equipements.filter((e) => e !== id) : [...equipements, id];
    pushParams({ equipements: suivants.join(",") });
  };
  const activeCount = [params.type, params.sort, params.price_min, params.price_max, params.petit_dejeuner].filter(Boolean).length + equipements.length;
  // Map of the searched area (listings have no coordinates yet: no pin per listing)
  const lieuCarte = params.city || "Lomé";
  const villeCarte = !params.city || QUARTIERS_LOME.includes(params.city) ? "Lomé, Togo" : "Togo";

  const typesChips = (
    <div className="flex flex-wrap gap-2">
      {TYPES.map((o) => (
        <button
          key={o.id}
          onClick={() => pushParams({ type: o.id })}
          aria-pressed={params.type === o.id}
          className={cn("px-3 py-2 rounded-full text-sm border transition-colors", params.type === o.id ? "bg-primary text-white border-primary" : "bg-white text-dark border-gray-200 hover:border-primary/40")}
        >
          {t(`types.${o.label}`)}
        </button>
      ))}
    </div>
  );

  const filtersPanel = (
    <div className="space-y-6">
      <div>
        <p className="text-xs text-muted font-bold uppercase tracking-wider mb-2">{t("typeLogement")}</p>
        {typesChips}
      </div>

      <div>
        <p className="text-xs text-muted font-bold uppercase tracking-wider mb-2">{t("equipements")}</p>
        <div className="flex flex-wrap gap-2">
          {[...EQUIPEMENTS_PRINCIPAUX, ...AUTRES_EQUIPEMENTS.filter((id) => tousEquipements || equipements.includes(id))].map((id) => [id, AMENITIES[id]] as const).map(([id, { label }]) => (
            <button
              key={id}
              onClick={() => basculerEquipement(id)}
              aria-pressed={equipements.includes(id)}
              className={cn("px-3 py-1.5 rounded-full text-sm border transition-colors", equipements.includes(id) ? "bg-primary text-white border-primary" : "bg-white text-dark border-gray-200 hover:border-primary/40")}
            >
              {label}
            </button>
          ))}
        </div>
        <button type="button" onClick={() => setTousEquipements((v) => !v)} aria-expanded={tousEquipements}
          className="mt-2 text-sm font-bold text-primary hover:underline">
          {tousEquipements ? t("moinsEquipements") : t("plusEquipements")}
        </button>
      </div>

      <div>
        <p className="text-xs text-muted font-bold uppercase tracking-wider mb-2">{t("trierPar")}</p>
        <Select
          label={t("trierPar")} value={params.sort}
          onChange={(v) => pushParams({ sort: v })}
          options={SORTS.map((o) => ({ value: o.id, label: t(`tris.${o.label}`) }))}
        />
      </div>

      <label className="flex items-center gap-3 cursor-pointer">
        <input type="checkbox" className="accent-primary w-5 h-5" checked={params.petit_dejeuner === "inclus"}
          onChange={(e) => pushParams({ petit_dejeuner: e.target.checked ? "inclus" : "" })} />
        <span className="text-sm font-semibold text-dark">{t("petitDejInclus")}</span>
      </label>

      <div>
        <p className="text-xs text-muted font-bold uppercase tracking-wider mb-2">{t("prixParNuit")}</p>
        <div className="flex items-center gap-2">
          <input type="number" inputMode="numeric" min={0} placeholder={t("min")} value={priceMin} onChange={(e) => setPriceMin(e.target.value)} className="w-full min-w-0 border border-gray-200 rounded-lg px-3 py-2 text-base sm:text-sm text-dark outline-none" />
          <span className="text-muted">-</span>
          <input type="number" inputMode="numeric" min={0} placeholder={t("max")} value={priceMax} onChange={(e) => setPriceMax(e.target.value)} className="w-full min-w-0 border border-gray-200 rounded-lg px-3 py-2 text-base sm:text-sm text-dark outline-none" />
        </div>
        <button onClick={() => submitSearch()} className="mt-3 w-full bg-primary text-white py-2.5 rounded-xl text-sm font-medium hover:bg-primary-700 transition-colors">
          {t("appliquer")}
        </button>
      </div>

      {activeCount > 0 && (
        <button
          onClick={() => { setPriceMin(""); setPriceMax(""); pushParams({ type: "", sort: "", price_min: "", price_max: "", petit_dejeuner: "", equipements: "" }); }}
          className="w-full text-sm font-semibold text-gray-500 hover:text-primary"
        >
          {t("effacerFiltres")}
        </button>
      )}
    </div>
  );

  return (
    <div className="min-h-screen bg-light">
      <div className="bg-white border-b border-gray-100 shadow-sm px-4 sm:px-6 py-4">
        <form method="post" onSubmit={submitSearch} className="max-w-7xl mx-auto grid grid-cols-2 lg:flex gap-2 sm:gap-3 items-stretch">
          <label className="col-span-2 lg:flex-1 flex items-center gap-3 border border-gray-200 rounded-xl px-4 py-3 bg-white focus-within:border-primary transition-colors">
            <Search size={16} className="text-muted flex-shrink-0" />
            <ChampDestination
              value={city} onChange={setCity}
              // Suggested city chosen: the search starts right away
              onVille={(ville) => pushParams({ city: ville })}
              placeholder={t("destinationExemple")}
              ariaLabel={t("destination")}
              className="flex-1 min-w-0"
              inputClassName="w-full text-base sm:text-sm text-dark placeholder:text-muted outline-none bg-transparent"
              listeClassName="-left-11 -right-4"
            />
          </label>
          <DateRangeField
            checkIn={checkIn} checkOut={checkOut}
            onChange={(a, d) => { setCheckIn(a); setCheckOut(d); }}
            className="col-span-2 lg:w-[20rem]"
          />
          <GuestsField value={Number(guests) || 1} onChange={(n) => setGuests(String(n))} className="lg:w-48" />
          <button type="submit" className="bg-primary text-white px-6 py-3 rounded-xl flex items-center justify-center gap-2 font-medium text-sm hover:bg-primary-700 transition-colors">
            <Search size={16} />
            {t("rechercher")}
          </button>
        </form>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
        <div className="flex gap-8">
          <aside className="w-64 flex-shrink-0 hidden lg:block">
            <div className="bg-white rounded-2xl shadow-card p-5 sticky top-24">
              <div className="flex items-center gap-2 mb-5">
                <SlidersHorizontal size={16} className="text-primary" />
                <h2 className="font-heading font-semibold text-dark">{t("filtres")}</h2>
              </div>
              {filtersPanel}
            </div>
          </aside>

          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between gap-3 mb-6">
              {isLoading ? (
                <p className="text-muted text-sm">{t("rechercheEnCours")}</p>
              ) : (
                <h1 className="text-dark font-medium">
                  <span className="font-heading font-bold text-2xl">{results.length}</span>{" "}
                  {t("hebergements", { nombre: results.length })}
                  {params.city && <span className="text-muted font-normal"> {t("aVille", { ville: params.city })}</span>}
                  {avecDates && <span className="text-muted font-normal text-sm"> · {t("disponiblesSurPeriode", { nombre: nbDisponibles, debut: formatDate(params.check_in, { day: "numeric", month: "numeric", year: "numeric" }), fin: formatDate(params.check_out, { day: "numeric", month: "numeric", year: "numeric" }) })}</span>}
                </h1>
              )}
              <div className="flex items-center gap-2 flex-shrink-0">
                {avecDates && (
                  <button onClick={() => pushParams({ disponibles: params.disponibles ? "" : "true" })} aria-pressed={Boolean(params.disponibles)}
                    className={cn("flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold border",
                      params.disponibles ? "bg-primary text-white border-primary" : "bg-white text-dark border-gray-200")}>
                    {t("disponiblesUniquement")}
                  </button>
                )}
                <button onClick={() => setCarte((c) => !c)} aria-pressed={carte} className="flex items-center gap-2 border border-gray-200 bg-white rounded-full px-4 py-2 text-sm font-semibold text-dark">
                  {carte ? <List size={15} /> : <IconeCarte size={15} />} {carte ? t("masquerCarte") : t("afficherCarte")}
                </button>
                <button onClick={() => setFiltersOpen(true)} className="lg:hidden flex items-center gap-2 border border-gray-200 bg-white rounded-full px-4 py-2 text-sm font-semibold text-dark">
                  <SlidersHorizontal size={15} /> {t("filtres")}{activeCount > 0 && <span className="bg-primary text-white text-[10px] rounded-full w-5 h-5 flex items-center justify-center">{activeCount}</span>}
                </button>
              </div>
            </div>

            {/* Types always visible on mobile (the other filters are in the "Filters" panel) */}
            <div className="lg:hidden -mt-2 mb-5 overflow-x-auto">{typesChips}</div>

            {carte && (
              <div className="mb-6 h-72 sm:h-96 rounded-2xl overflow-hidden shadow-card bg-white">
                <MapEmbed lieu={lieuCarte} ville={villeCarte} />
              </div>
            )}

            {isError ? (
              <div className="bg-white rounded-2xl shadow-card p-12 text-center">
                <p className="text-dark font-semibold mb-2">{t("erreurChargement")}</p>
                <button onClick={() => refetch()} className="text-primary font-bold hover:underline">{t("reessayer")}</button>
              </div>
            ) : isLoading ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-5">
                {[0, 1, 2, 3, 4, 5].map((i) => <div key={i} className="h-72 rounded-2xl skeleton" />)}
              </div>
            ) : results.length === 0 && aucunLogement ? (
              <BandeauBientot />
            ) : results.length === 0 ? (
              <div className="bg-white rounded-2xl shadow-card p-10 sm:p-16 text-center">
                <div className="mx-auto w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mb-4">
                  <Search size={28} className="text-primary" />
                </div>
                <p className="text-dark font-heading font-semibold text-xl mb-2">{t("aucunResultat")}</p>
                <p className="text-muted">{t("aucunResultatTexte")}</p>
                <button onClick={() => router.push(pathname)} className="mt-4 text-primary font-bold hover:underline">{t("voirTous")}</button>
              </div>
            ) : (
              <section aria-labelledby="liste-resultats" className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-5">
                <h2 id="liste-resultats" className="sr-only">{t("listeResultats")}</h2>
                {results.map((h) => <PropertyCard key={h.id} property={h} query={stayQuery} />)}
              </section>
            )}
          </div>
        </div>
      </div>

      {filtersOpen && (
        <div className="lg:hidden fixed inset-0 z-[60]" role="dialog" aria-modal="true" aria-label={t("filtres")}>
          <div className="absolute inset-0 bg-black/40" onClick={() => setFiltersOpen(false)} />
          <div className="absolute bottom-0 inset-x-0 bg-white rounded-t-3xl p-5 pb-8 max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-5">
              <h2 className="font-heading font-bold text-lg text-dark">{t("filtres")}</h2>
              <button onClick={() => setFiltersOpen(false)} className="p-2 -mr-2" aria-label={t("fermer")}><X size={20} /></button>
            </div>
            {filtersPanel}
          </div>
        </div>
      )}
    </div>
  );
}

export default function RecherchePage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-light flex items-center justify-center"><p className="text-muted"><Chargement /></p></div>}>
      <RechercheContent />
    </Suspense>
  );
}
