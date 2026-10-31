import type { MoyenPaiement } from "@/types/api/paiement";

export type CodeCause = "education" | "sante" | "eau" | "environnement";

export interface Cause {
  code: CodeCause;
  nom: string;
  description: string;
}

export interface ConfigGive {
  actif: boolean;
  moyens: MoyenPaiement[];
  montants_suggeres: number[];
  montant_min: number;
  montant_max: number;
  /** Average fees of the payment provider (0.03 = 3 %). */
  frais_paiement: number;
  /** Kwa-Ba's commission on donations: 0 at launch. */
  commission_kwaba: number;
  /** A month's donations are transferred at the latest on this day of the following month. */
  jour_reversement: number;
  fcfa_par_euro: number;
  causes: Cause[];
}

export interface Organisation {
  id: string;
  nom: string;
  slug: string;
  cause: CodeCause;
  pays: "TG" | "BJ" | "BF" | "NE" | "ML";
  ville: string;
  resume: string;
  logo: string | null;
  image: string | null;
  impact: { collecte: number; nb_dons: number };
}

export interface Projet {
  id: string;
  titre: string;
  cause: CodeCause;
  resume: string;
  description: string;
  lieu: string;
  objectif: number | null;
  image: string | null;
  collecte: number;
}

export interface Reversement {
  id: string;
  reference: string;
  organisation: { nom: string; slug: string };
  periode: string;
  montant: number;
  nb_dons: number;
  statut: "a_effectuer" | "effectue";
  date_prevue: string;
  effectue_le: string | null;
  moyen: "virement" | "mobile_money" | "";
  reference_operation: string;
  justificatif: string | null;
  note: string;
}

export interface Impact {
  collecte: number;
  reverse: number;
  en_attente: number;
  nb_dons: number;
  nb_donateurs: number;
}

export interface OrganisationDetail extends Omit<Organisation, "impact"> {
  description: string;
  site_web: string;
  numero_enregistrement: string;
  verifiee_le: string;
  verification: string;
  impact: Impact;
  projets: Projet[];
  reversements: Reversement[];
}

export interface ReponseDons {
  results: Don[];
  total_donne: number;
  nb_payes: number;
}

export interface ImpactGlobal extends Impact {
  nb_organisations: number;
  causes: { code: CodeCause; nom: string; collecte: number; nb_dons: number }[];
  reversements: Reversement[];
}

export type StatutDon = "en_attente" | "paye" | "echoue";

export interface Don {
  id: string;
  reference: string;
  organisation: { nom: string; slug: string; cause: CodeCause };
  projet: { id: string; titre: string } | null;
  montant: number;
  couvre_frais: boolean;
  frais: number;
  total: number;
  montant_ong: number;
  moyen: MoyenPaiement;
  partage_identite: boolean;
  statut: StatutDon;
  paye_le: string | null;
  date_reversement: string | null;
  reversement: { reference: string; statut: Reversement["statut"]; effectue_le: string | null; justificatif: string | null } | null;
  cree_le: string;
}
