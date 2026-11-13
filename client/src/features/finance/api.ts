import api from "@/lib/api";

// --- Back-office: the ledger of money movements (module finance, ADR-024)

export interface InvariantFinance {
  invariant: string;
  libelle: string;
  /** 0: the invariant holds */
  anomalies: number;
}

export interface DuPartenaire {
  tiers_type: string;
  tiers_id: string | null;
  /** Empty for a third party that is not an account (driver, rental partner) */
  nom: string;
  email: string;
  solde_du: number;
}

export interface MouvementFinance {
  id: number;
  date_evenement: string;
  famille: string;
  nature_code: string;
  nature_libelle: string;
  offre_code: string;
  tiers_type: string | null;
  tiers_id: string | null;
  nom: string;
  email: string;
  compte_argent_code: string;
  moyen_paiement_code: string | null;
  piece_reference: string | null;
  montant: number;
  /** Positive: money in; negative: money out */
  montant_signe: number;
  origine: string;
  annule_mouvement_id: number | null;
}

export interface GrandLivre {
  invariants: InvariantFinance[];
  soldes: {
    revenu_du_mois: number;
    du_partenaires: number;
    du_voyageurs: number;
    cautions_detenues: number;
    comptes: Record<string, number>;
  };
  du_aux_partenaires: DuPartenaire[];
  mouvements: MouvementFinance[];
}

export async function lireGrandLivre() {
  return (await api.get<GrandLivre>("/v1/admin/finance/grand-livre/")).data;
}
