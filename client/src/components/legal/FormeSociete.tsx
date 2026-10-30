"use client";

import { useLocale } from "next-intl";
import { useReglagesSite } from "@/lib/site";

/**
 * Legal form of KWA-BA, with "en formation" until the RCCM (SOCIETE_EN_FORMATION of server/.env): setting the variable
 * to False the day of the registration is enough, without touching the code. Shown "en formation" while the settings
 * are not read, never the reverse.
 */
export default function FormeSociete() {
  const enFormation = useReglagesSite().data?.en_formation !== false;
  if (useLocale() === "en") return <>a simplified joint-stock company (SAS){enFormation && " in the process of incorporation"}</>;
  return <>société par actions simplifiée (SAS){enFormation && " en formation"}</>;
}
