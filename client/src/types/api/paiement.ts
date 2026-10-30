export interface OperateurPaiement {
  code: string;
  nom: string;
}

export interface PaysPaiement {
  code: "TG" | "BJ" | "BF" | "NE" | "ML";
  nom: string;
  indicatif: string;
  chiffres: number;
  operateurs: OperateurPaiement[];
}

export type MoyenPaiement = "mobile_money" | "carte" | "paypal";

export interface DevisSejour {
  prix_nuits: number;
  frais_service: number;
  total: number;
}

export interface ConfigPaiement {
  actif: boolean;
  /** Offered methods: mobile_money and carte go through FedaPay, paypal is charged in euros. */
  moyens: MoyenPaiement[];
  fcfa_par_euro: number;
  environnement: "sandbox" | "live";
  frais_voyageur: number;
  /** Reduced fees: loyal customer, Stay Pack + Driver. */
  frais_reduits: number;
  commission_hote: number;
  /** Commission by partner type (price grid). */
  commissions: { particulier: number; hotel: number; fondateur: number };
  delai_paiement_minutes: number;
  pays: PaysPaiement[];
}

export type StatutPaiement = "en_attente" | "reussi" | "echoue" | "annule";

export interface StatutPaiementReservation {
  reservation: "pending" | "confirmed" | "cancelled";
  paiement: StatutPaiement | null;
  expire_le: string | null;
  annule_par: string;
}

export interface ProfilVersement {
  pays: PaysPaiement["code"];
  operateur: string;
  numero: string;
  titulaire: string;
  mis_a_jour_le?: string;
}

export type StatutVersement = "planifie" | "en_cours" | "envoye" | "echoue";

export interface Versement {
  id: string;
  reservation_id: string;
  reference: string;
  hebergement: string;
  voyageur: string;
  check_in: string;
  check_out: string;
  montant_brut: number;
  commission: number;
  montant: number;
  statut: StatutVersement;
  date_prevue: string;
  envoye_le: string | null;
  probleme: string;
}

export interface Revenus {
  totaux: { a_venir: number; en_cours: number; verse: number; commission: number };
  profil_complet: boolean;
  /** This host's commission today, in % (8, 12 for a hotel, 5 during the Founders Programme). */
  commission_pourcent: number;
  /** Partner type set by the team: individual (8 %), hotel (12 %), founder (5 % for 6 months). */
  partenaire: "particulier" | "hotel" | "fondateur";
  frais_voyageur_pourcent: number;
  versements: Versement[];
}
