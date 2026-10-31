"use client";

import { useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { Briefcase, Car, ChevronLeft, ChevronRight, Fuel, Snowflake, Users } from "lucide-react";
import { cn } from "@/lib/utils";
import { useFormat } from "@/lib/format";
import type { CategorieVehicule, Formule } from "./types";

function Galerie({ photos, nom }: { photos: string[]; nom: string }) {
  const t = useTranslations("location");
  const rail = useRef<HTMLDivElement>(null);
  const [index, setIndex] = useState(0);
  if (!photos.length) return <Car size={56} className="text-gray-300" aria-hidden />;
  const aller = (i: number) => rail.current?.scrollTo({ left: i * rail.current.clientWidth, behavior: "smooth" });
  const fleche = "absolute top-1/2 -translate-y-1/2 w-9 h-9 rounded-full bg-white/90 text-dark shadow flex items-center justify-center opacity-0 group-hover:opacity-100 focus-visible:opacity-100 transition-opacity";
  return (
    <div className="relative w-full h-full group">
      <div ref={rail} className="flex w-full h-full overflow-x-auto snap-x snap-mandatory scrollbar-hide"
        onScroll={(e) => setIndex(Math.round(e.currentTarget.scrollLeft / e.currentTarget.clientWidth))}>
        {photos.map((src, i) => (
          // eslint-disable-next-line @next/next/no-img-element
          <img key={src} src={src} alt={photos.length > 1 ? t("photoNumero", { nom, numero: i + 1, total: photos.length }) : ""}
            loading={i ? "lazy" : undefined} className="w-full h-full flex-shrink-0 object-cover snap-center" />
        ))}
      </div>
      {photos.length > 1 && (
        <>
          {index > 0 && <button type="button" onClick={() => aller(index - 1)} aria-label={t("photoPrecedente")} className={cn(fleche, "left-2")}><ChevronLeft size={18} aria-hidden /></button>}
          {index < photos.length - 1 && <button type="button" onClick={() => aller(index + 1)} aria-label={t("photoSuivante")} className={cn(fleche, "right-2")}><ChevronRight size={18} aria-hidden /></button>}
          <div className="absolute bottom-2 inset-x-0 flex justify-center gap-1.5" aria-hidden>
            {photos.map((src, i) => <span key={src} className={cn("w-1.5 h-1.5 rounded-full transition-colors", i === index ? "bg-white" : "bg-white/50")} />)}
          </div>
        </>
      )}
    </div>
  );
}

export default function CarteVehicule({ c, formule, prixChauffeur, onChoisir }: {
  c: CategorieVehicule; formule: Formule; prixChauffeur: number; onChoisir: () => void;
}) {
  const { formatPrice } = useFormat();
  const t = useTranslations("location");
  const propose = formule === "avec_chauffeur" ? c.formules.avec_chauffeur : c.formules.sans_chauffeur;
  return (
    <article className="bg-white rounded-3xl border border-gray-100 shadow-sm overflow-hidden flex flex-col">
      <div className="h-40 bg-gray-50 flex items-center justify-center relative">
        <Galerie photos={c.photos?.length ? c.photos : c.image ? [c.image] : []} nom={c.nom} />
        {formule === "sans_chauffeur" && c.caution === 0 && (
          <span className="absolute top-3 left-3 bg-secondary text-white text-xs font-bold px-2.5 py-1 rounded-full">{t("sansCaution")}</span>
        )}
      </div>
      <div className="p-5 flex flex-col flex-1">
        <p className="text-xs font-bold uppercase tracking-wide text-primary">{t(`gammes.${c.gamme}`)}</p>
        <h2 className="font-heading font-bold text-dark text-lg mt-1">{c.nom}</h2>
        {c.exemple_modele && <p className="text-sm text-gray-500">{c.exemple_modele}{c.annee ? ` · ${c.annee}` : ""}</p>}
        <ul className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-gray-600 mt-3">
          <li className="flex items-center gap-1.5"><Users size={15} /> {t("places", { nombre: c.places })}</li>
          <li className="flex items-center gap-1.5"><Briefcase size={15} /> {t("bagages", { nombre: c.bagages })}</li>
          <li>{t(`boites.${c.boite}`)}</li>
          <li className="flex items-center gap-1.5"><Fuel size={15} /> {t(`carburants.${c.carburant}`)}</li>
          {c.climatisation && <li className="flex items-center gap-1.5"><Snowflake size={15} /> {t("clim")}</li>}
        </ul>
        {formule === "sans_chauffeur" && c.caution > 0 && <p className="text-xs text-gray-500 mt-2">{t("cautionMontant", { montant: formatPrice(c.caution) })}</p>}
        <div className="flex items-end justify-between gap-3 mt-auto pt-4">
          {propose ? (
            <div>
              <p className="font-heading font-bold text-dark text-xl">{formatPrice(c.prix_jour)}<span className="text-xs font-normal text-gray-500">{t("parJour")}</span></p>
              {formule === "avec_chauffeur" && <p className="text-xs text-gray-500">{t("plusChauffeur", { prix: formatPrice(prixChauffeur) })}</p>}
            </div>
          ) : (
            <p className="text-sm text-gray-400">{t("nonProposee")}</p>
          )}
          <button onClick={onChoisir} disabled={!propose}
            className="relative zone-tactile flex items-center gap-1 px-5 py-2.5 rounded-xl bg-primary text-white text-sm font-bold disabled:opacity-40">
            {t("choisir")} <ChevronRight size={16} />
          </button>
        </div>
      </div>
    </article>
  );
}
