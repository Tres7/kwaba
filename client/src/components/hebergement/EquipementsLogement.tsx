"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import AmenityBadge, { estRegle, useEquipements } from "@/components/hebergement/AmenityBadge";

/** Beyond this number, the list is folded (the first categories stay visible). */
const PLIAGE = 10;

/** Listing page: amenities by category, then the house rules the host gave. */
export default function EquipementsLogement({ amenities }: { amenities: string[] }) {
  const { CATEGORIES_EQUIPEMENTS, REGLES } = useEquipements();
  const t = useTranslations("fiche");
  const [deplie, setDeplie] = useState(false);
  const equipements = amenities.filter((a) => !estRegle(a));
  const regles = REGLES.map((r) => (amenities.includes(r.oui.id) ? r.oui.id : amenities.includes(r.non.id) ? r.non.id : null))
    .filter((r): r is string => r !== null);

  const connus = new Set(CATEGORIES_EQUIPEMENTS.flatMap((c) => c.equipements.map((e) => e.id)));
  const groupes = [
    ...CATEGORIES_EQUIPEMENTS.map((c) => ({ id: c.id, label: c.label, ids: c.equipements.map((e) => e.id).filter((id) => equipements.includes(id)) })),
    // Values unknown to this version of the site: shown as they are, at the end
    { id: "autres", label: "", ids: equipements.filter((a) => !connus.has(a)) },
  ].filter((g) => g.ids.length > 0);

  // Folded: whole categories until about PLIAGE amenities are shown
  let restants = deplie ? Infinity : PLIAGE;
  const visibles = groupes.filter((g, i) => {
    if (i > 0 && restants <= 0) return false;
    restants -= g.ids.length;
    return true;
  });
  const parCategorie = groupes.length > 1;

  return (
    <>
      {equipements.length === 0 ? (
        <p className="text-muted text-sm">{t("aucunEquipement")}</p>
      ) : (
        <div className="space-y-5">
          {visibles.map((g) => (
            <div key={g.id}>
              {parCategorie && g.label && <h3 className="text-xs font-bold uppercase tracking-wide text-gray-500 mb-2.5">{g.label}</h3>}
              <div className="grid grid-cols-2 sm:flex sm:flex-wrap gap-3">
                {g.ids.map((a) => <AmenityBadge key={a} amenity={a} />)}
              </div>
            </div>
          ))}
          {visibles.length < groupes.length || deplie ? (
            <button type="button" onClick={() => setDeplie((d) => !d)} aria-expanded={deplie}
              className="text-sm font-bold text-primary hover:underline">
              {deplie ? t("voirMoinsEquipements") : t("voirTousEquipements", { nombre: equipements.length })}
            </button>
          ) : null}
        </div>
      )}

      {regles.length > 0 && (
        <div className="mt-6 pt-5 border-t border-gray-100">
          <h3 className="font-heading font-bold text-dark text-base mb-3">{t("reglesMaison")}</h3>
          <div className="grid grid-cols-2 sm:flex sm:flex-wrap gap-3">
            {regles.map((r) => <AmenityBadge key={r} amenity={r} />)}
          </div>
        </div>
      )}
    </>
  );
}
