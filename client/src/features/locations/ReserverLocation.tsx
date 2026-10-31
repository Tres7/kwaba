"use client";

import { useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import PageHero from "@/components/layout/PageHero";
import { BadgeCheck, Car, UserRound } from "lucide-react";
import { Link } from "@/i18n/navigation";
import { cn } from "@/lib/utils";
import { useModule } from "@/lib/site";
import { useFormat } from "@/lib/format";
import { useCatalogue } from "./hooks";
import CarteVehicule from "./CarteVehicule";
import FormulaireLocation from "./FormulaireLocation";
import MesLocations from "./MesLocations";
import type { CategorieVehicule, Formule } from "./types";

// "I drive" (without a driver) is not in the launch offer: offered only if its switch is on
const FORMULES: Formule[] = ["avec_chauffeur", "sans_chauffeur", "chauffeur_seul"];

function Puce({ actif, onClick, children }: { actif: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button type="button" aria-pressed={actif} onClick={onClick}
      className={cn("relative zone-tactile px-4 py-2 rounded-full text-sm font-semibold border transition-colors whitespace-nowrap",
        actif ? "bg-primary text-white border-primary" : "bg-white text-dark border-gray-200 hover:border-primary/40")}>
      {children}
    </button>
  );
}

/** Vehicle photos: swipe scrolling (snapping), arrows on hover on computers, position dots. */
export default function LocationPage() {
  const { formatPrice } = useFormat();
  const t = useTranslations("location");
  const tNav = useTranslations("nav");
  const [formule, setFormule] = useState<Formule>("avec_chauffeur");
  const [gamme, setGamme] = useState<string | null>(null);
  const [boite, setBoite] = useState<string | null>(null);
  const [placesMin, setPlacesMin] = useState<number | null>(null);
  const [choix, setChoix] = useState<CategorieVehicule | null>(null);
  const sansChauffeur = useModule("location_sans_chauffeur");
  const formules = FORMULES.filter((f) => f !== "sans_chauffeur" || sansChauffeur);

  const { data: catalogue, isLoading } = useCatalogue();

  const categories = useMemo(() => catalogue?.categories ?? [], [catalogue]);
  const gammes = (catalogue?.filtres?.gammes ?? []).filter((g) => categories.some((c) => c.gamme === g.code));
  const paliersPlaces = [5, 7, 9].filter((n) => categories.some((c) => c.places >= n));
  const visibles = categories.filter((c) =>
    (!gamme || c.gamme === gamme) && (!boite || c.boite === boite) && (!placesMin || c.places >= placesMin));

  return (
    <div className="bg-light min-h-[70vh]">
      <PageHero surtitre={<><Car size={16} /> {tNav("location")}</>} titre={t("titre")} sousTitre={t(sansChauffeur ? "sousTitreSansChauffeur" : "sousTitre")} />
      <div className="max-w-6xl mx-auto px-4 sm:px-6 pb-12">

        {isLoading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5 mt-8">{[0, 1, 2].map((i) => <div key={i} className="h-80 skeleton rounded-3xl" />)}</div>
        ) : !catalogue?.active ? (
          <div className="bg-white rounded-3xl border border-gray-100 p-10 text-center mt-8">
            <Car size={40} className="mx-auto text-primary" aria-hidden />
            <p className="font-heading font-bold text-dark text-xl mt-4">{t("bientot")}</p>
            <p className="text-gray-600 mt-2">{t("bientotAide")}</p>
            <Link href="/transfert" className="inline-block mt-5 px-6 py-3 rounded-xl bg-primary text-white font-bold">{tNav("transfertAeroport")}</Link>
          </div>
        ) : choix ? (
          <div className="mt-8">
            <FormulaireLocation catalogue={catalogue} categorie={choix} formule={formule} onChanger={() => setChoix(null)} />
          </div>
        ) : (
          <>
            <div className="mt-8 space-y-4">
              <div className="inline-flex flex-wrap bg-white border border-gray-200 rounded-3xl sm:rounded-full p-1" role="group" aria-label={t("formule")}>
                {formules.map((f) => (
                  <button key={f} type="button" aria-pressed={formule === f} onClick={() => setFormule(f)}
                    className={cn("relative zone-tactile px-5 py-2 rounded-full text-sm font-bold transition-colors", formule === f ? "bg-primary text-white" : "text-dark")}>
                    {t(`formules.${f}`)}
                  </button>
                ))}
              </div>
              <ul className="flex flex-wrap gap-x-5 gap-y-1 text-sm text-gray-600">
                <li className="flex items-center gap-1.5"><BadgeCheck size={15} className="text-secondary" /> {t("argumentVerifie")}</li>
                <li className="flex items-center gap-1.5"><BadgeCheck size={15} className="text-secondary" /> {t("argumentSansFrais")}</li>
                {formule !== "sans_chauffeur" && <li className="flex items-center gap-1.5"><UserRound size={15} className="text-secondary" /> {t("argumentChauffeur", { prix: formatPrice(catalogue.chauffeur?.prix_jour ?? 7000) })}</li>}
              </ul>
              {formule !== "chauffeur_seul" && (
                <>
                  <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
                    <Puce actif={!gamme} onClick={() => setGamme(null)}>{t("tous")}</Puce>
                    {gammes.map((g) => <Puce key={g.code} actif={gamme === g.code} onClick={() => setGamme(g.code)}>{t(`gammes.${g.code}`)}</Puce>)}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {(["automatique", "manuelle"] as const).filter((b) => categories.some((c) => c.boite === b)).map((b) => (
                      <Puce key={b} actif={boite === b} onClick={() => setBoite(boite === b ? null : b)}>{t(`boites.${b}`)}</Puce>
                    ))}
                    {paliersPlaces.map((n) => (
                      <Puce key={n} actif={placesMin === n} onClick={() => setPlacesMin(placesMin === n ? null : n)}>{t("placesMin", { nombre: n })}</Puce>
                    ))}
                  </div>
                </>
              )}
            </div>

            {formule === "chauffeur_seul" ? (
              <div className="mt-6">
                <FormulaireLocation catalogue={catalogue} categorie={null} formule="chauffeur_seul" onChanger={() => setFormule("avec_chauffeur")} />
              </div>
            ) : visibles.length === 0 ? (
              <p className="bg-white rounded-3xl border border-gray-100 p-10 text-center text-gray-500 mt-6">{t("aucun")}</p>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5 mt-6">
                {visibles.map((c) => (
                  <CarteVehicule key={c.id} c={c} formule={formule} prixChauffeur={catalogue.chauffeur?.prix_jour ?? 7000}
                    onChoisir={() => { setChoix(c); window.scrollTo({ top: 0, behavior: "smooth" }); }} />
                ))}
              </div>
            )}
          </>
        )}

        <MesLocations />
      </div>
    </div>
  );
}
