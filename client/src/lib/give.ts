import { useQuery } from "@tanstack/react-query";
import { BookOpen, Droplets, HeartPulse, Leaf } from "lucide-react";
import api from "@/lib/api";
import { langue, selon } from "@/lib/utils";
import type { CodeCause, ConfigGive } from "@/types/api/give";

const TEXTES_CAUSES: Record<CodeCause, { fr: [string, string]; en: [string, string] }> = {
  education: { fr: ["Éducation", "Écoles, fournitures, bourses et soutien scolaire."], en: ["Education", "Schools, supplies, scholarships and tutoring."] },
  sante: { fr: ["Santé", "Soins, centres de santé, prévention et accès aux médicaments."], en: ["Health", "Care, health centres, prevention and access to medicines."] },
  eau: { fr: ["Accès à l'eau", "Forages, puits, assainissement et hygiène."], en: ["Water access", "Boreholes, wells, sanitation and hygiene."] },
  environnement: { fr: ["Environnement", "Reboisement, gestion des déchets, protection des côtes."], en: ["Environment", "Reforestation, waste management, coastal protection."] },
};

function cause(code: CodeCause, icon: typeof BookOpen, couleur: string) {
  return {
    icon, couleur,
    get nom() { return selon(TEXTES_CAUSES[code])[0]; },
    get description() { return selon(TEXTES_CAUSES[code])[1]; },
  };
}

/** Supported causes: name and description in the current language. */
export const CAUSES: Record<CodeCause, { nom: string; description: string; icon: typeof BookOpen; couleur: string }> = {
  education: cause("education", BookOpen, "bg-amber-100 text-amber-800"),
  sante: cause("sante", HeartPulse, "bg-rose-100 text-rose-800"),
  eau: cause("eau", Droplets, "bg-sky-100 text-sky-800"),
  environnement: cause("environnement", Leaf, "bg-emerald-100 text-emerald-800"),
};

const NOMS_PAYS: Record<string, { fr: string; en: string }> = {
  TG: { fr: "Togo", en: "Togo" }, BJ: { fr: "Bénin", en: "Benin" }, BF: { fr: "Burkina Faso", en: "Burkina Faso" },
  NE: { fr: "Niger", en: "Niger" }, ML: { fr: "Mali", en: "Mali" },
};

/** Country names, in the current language (PAYS[code]). */
export const PAYS: Record<string, string> = new Proxy(NOMS_PAYS as unknown as Record<string, string>, {
  get: (_, code: string) => (NOMS_PAYS[code] ? selon(NOMS_PAYS[code]) : undefined),
});

/** Public donation settings: suggested amounts, fees, transfer schedule. */
export function useConfigGive() {
  return useQuery({
    queryKey: ["give", "config"],
    queryFn: async () => (await api.get<ConfigGive>("/v1/give/config/")).data,
    staleTime: 60 * 1000,
  });
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

export function moisAnnee(iso: string): string {
  return new Date(`${iso}T00:00:00`).toLocaleDateString(langue() === "en" ? "en-GB" : "fr-FR", { month: "long", year: "numeric" });
}
