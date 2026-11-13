"use client";

import { useLocale } from "next-intl";
import { Backpack, BedDouble, Building, Building2, Hotel, House, Sofa, TreePalm, type LucideIcon } from "lucide-react";
import { cn, libelleType } from "@/lib/utils";
import type { HebergementType } from "@/types/api/models";

/** Kwa-Ba taxonomy (brief AN-TAX), in the order of the search filters and of the host's choice. */
export const TYPES_LOGEMENT: HebergementType[] = [
  "chambre_privee", "studio", "appartement", "maison_entiere", "villa", "chambre_hotel", "residence", "auberge",
];

export const ICONES_TYPES: Record<HebergementType, LucideIcon> = {
  chambre_privee: BedDouble, studio: Sofa, appartement: Building2, maison_entiere: House, villa: TreePalm,
  chambre_hotel: Hotel, residence: Building, auberge: Backpack,
};

/**
 * Local name in large, international name in a small badge: "Appartement" + "Apartment". In English, the other way
 * round. No badge when both names are the same (Studio, Villa).
 */
export function LibelleType({ type, className }: { type: string; className?: string }) {
  const langue = useLocale() === "en" ? "en" : "fr";
  const principal = libelleType(type, langue);
  const autre = libelleType(type, langue === "fr" ? "en" : "fr");
  return (
    <span className={cn("inline-flex flex-wrap items-center gap-x-1.5 gap-y-0.5", className)}>
      <span>{principal}</span>
      {autre !== principal && (
        <small lang={langue === "fr" ? "en" : "fr"}
          className="px-1.5 py-px rounded-full bg-primary-50 text-brand text-[10px] font-semibold normal-case tracking-normal leading-4">
          {autre}
        </small>
      )}
    </span>
  );
}
