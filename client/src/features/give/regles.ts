import { BookOpen, Droplets, HeartPulse, Leaf } from "lucide-react";
import { useLocale } from "next-intl";
import { useNomsPays } from "@/lib/pays";
import type { CodeCause } from "./types";

const TEXTES_CAUSES: Record<CodeCause, { fr: [string, string]; en: [string, string] }> = {
  education: { fr: ["Éducation", "Écoles, fournitures, bourses et soutien scolaire."], en: ["Education", "Schools, supplies, scholarships and tutoring."] },
  sante: { fr: ["Santé", "Soins, centres de santé, prévention et accès aux médicaments."], en: ["Health", "Care, health centres, prevention and access to medicines."] },
  eau: { fr: ["Accès à l'eau", "Forages, puits, assainissement et hygiène."], en: ["Water access", "Boreholes, wells, sanitation and hygiene."] },
  environnement: { fr: ["Environnement", "Reboisement, gestion des déchets, protection des côtes."], en: ["Environment", "Reforestation, waste management, coastal protection."] },
};

function creerTextes(langue: "fr" | "en") {
  const cause = (code: CodeCause, icon: typeof BookOpen, couleur: string) => {
    const [nom, description] = TEXTES_CAUSES[code][langue];
    return { nom, description, icon, couleur };
  };
  return {
    /** Supported causes: name and description. */
    CAUSES: {
      education: cause("education", BookOpen, "bg-amber-100 text-amber-800"),
      sante: cause("sante", HeartPulse, "bg-rose-100 text-rose-800"),
      eau: cause("eau", Droplets, "bg-sky-100 text-sky-800"),
      environnement: cause("environnement", Leaf, "bg-emerald-100 text-emerald-800"),
    } as Record<CodeCause, { nom: string; description: string; icon: typeof BookOpen; couleur: string }>,
  };
}

const TEXTES = { fr: creerTextes("fr"), en: creerTextes("en") };

/** Causes and countries in the language of the page. */
export function useTextesGive() {
  return { ...TEXTES[useLocale() === "en" ? "en" : "fr"], PAYS: useNomsPays() };
}

/** Same calculation as the server (apps/give/montants.py): shown before payment. */
export function calculerDon(montant: number, couvreFrais: boolean, taux: number) {
  if (couvreFrais) {
    const total = Math.ceil(montant / (1 - taux));
    return { frais: total - montant, total, montantOng: montant };
  }
  const frais = Math.round(montant * taux);
  return { frais, total: montant, montantOng: montant - frais };
}

/** Deadline of the transfer to the NGO for a donation made today. */
export function dateReversement(jour: number, depuis = new Date()): Date {
  return new Date(depuis.getFullYear(), depuis.getMonth() + 1, jour);
}
