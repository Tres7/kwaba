import { BathtubIcon, BedIcon, ClockIcon, CoffeeIcon, DoorOpenIcon, RulerIcon, type Icon } from "@phosphor-icons/react";
import { useTranslations } from "next-intl";
import type { Hebergement } from "@/types/api/models";
import { useFormat } from "@/lib/format";

type Details = Pick<Hebergement, "surface_m2" | "chambres" | "salles_de_bain" | "lits_doubles" | "lits_simples" | "canapes_lits"
  | "petit_dejeuner" | "petit_dejeuner_prix" | "arrivee_a_partir" | "depart_avant">;

/** « 14:00:00 » → « 14 h », « 10:30:00 » → « 10 h 30 ». */
const heure = (h: string | null) => {
  if (!h) return null;
  const [hh, mm] = h.split(":");
  return mm === "00" ? `${Number(hh)} h` : `${Number(hh)} h ${mm}`;
};
export const nombreLits = (d: Details) => (d.lits_doubles ?? 0) + (d.lits_simples ?? 0) + (d.canapes_lits ?? 0);

/** Short summary for cards: "140 m² · 3 bedrooms · Breakfast included". */
export function useResumeDetails() {
  const t = useTranslations("details");
  return (d: Details) => [
    d.surface_m2 ? t("surface", { m2: d.surface_m2 }) : null,
    d.chambres ? t("chambres", { nombre: d.chambres }) : null,
    d.petit_dejeuner === "inclus" ? t("petitDejInclusCourt") : null,
  ].filter(Boolean).join(" · ");
}

function Ligne({ Icone, titre, texte }: { Icone: Icon; titre: string; texte: string }) {
  return (
    <div className="flex items-center gap-3 bg-light-muted rounded-xl px-3 py-2.5">
      <span className="h-8 w-8 rounded-lg bg-white text-primary shadow-sm flex items-center justify-center flex-shrink-0">
        <Icone size={20} weight="duotone" aria-hidden />
      </span>
      <span className="min-w-0">
        <span className="block text-xs text-gray-500">{titre}</span>
        <span className="block text-sm font-semibold text-dark">{texte}</span>
      </span>
    </div>
  );
}

/** The listing in detail (page): area, bedrooms, beds, bathrooms, breakfast, times. Nothing for a listing without details. */
export default function DetailsLogement({ h }: { h: Details }) {
  const { formatPrice } = useFormat();
  const t = useTranslations("details");
  const lits = [
    h.lits_doubles ? t("litsDoubles", { nombre: h.lits_doubles }) : null,
    h.lits_simples ? t("litsSimples", { nombre: h.lits_simples }) : null,
    h.canapes_lits ? t("canapesLits", { nombre: h.canapes_lits }) : null,
  ].filter(Boolean).join(" · ");
  const petitDej = h.petit_dejeuner === "inclus" ? t("petitDejInclus")
    : h.petit_dejeuner === "option" ? t("petitDejOption", { prix: formatPrice(h.petit_dejeuner_prix ?? 0) })
    : h.petit_dejeuner === "non" ? t("petitDejNon") : null;
  const horaires = [heure(h.arrivee_a_partir) && t("arrivee", { heure: heure(h.arrivee_a_partir)! }),
    heure(h.depart_avant) && t("depart", { heure: heure(h.depart_avant)! })].filter(Boolean).join(" · ");

  const lignes: { Icone: Icon; titre: string; texte: string }[] = [];
  if (h.surface_m2) lignes.push({ Icone: RulerIcon, titre: t("surfaceTitre"), texte: t("surface", { m2: h.surface_m2 }) });
  if (h.chambres) lignes.push({ Icone: DoorOpenIcon, titre: t("chambresTitre"), texte: t("chambres", { nombre: h.chambres }) });
  if (lits) lignes.push({ Icone: BedIcon, titre: t("litsTitre", { nombre: nombreLits(h) }), texte: lits });
  if (h.salles_de_bain) lignes.push({ Icone: BathtubIcon, titre: t("sallesTitre"), texte: t("salles", { nombre: h.salles_de_bain }) });
  if (petitDej) lignes.push({ Icone: CoffeeIcon, titre: t("petitDejTitre"), texte: petitDej });
  if (horaires) lignes.push({ Icone: ClockIcon, titre: t("horairesTitre"), texte: horaires });
  if (!lignes.length) return null;

  return (
    <section className="bg-white rounded-2xl shadow-card p-5 sm:p-6">
      <h2 className="font-heading font-bold text-dark text-xl mb-4">{t("titre")}</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {lignes.map((l) => <Ligne key={l.titre} {...l} />)}
      </div>
    </section>
  );
}
