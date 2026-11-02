export type Formule = "sans_chauffeur" | "avec_chauffeur" | "chauffeur_seul";
export type StatutLocation = "en_attente_paiement" | "confirmee" | "partenaire_assigne" | "terminee" | "annulee";

/** Vehicle of a partner owner (never named on the site). */
export interface CategorieVehicule {
  id: number;
  nom: string;
  gamme: string;
  gamme_libelle: string;
  exemple_modele: string;
  description: string;
  places: number;
  bagages: number;
  boite: "manuelle" | "automatique";
  carburant: string;
  climatisation: boolean;
  annee: number | null;
  /** Main photo (first of `photos`). */
  image: string | null;
  photos: string[];
  /** Vehicle price per day, set by the owner; the driver is charged on top. */
  prix_jour: number;
  formules: { sans_chauffeur: boolean; avec_chauffeur: boolean };
  /** Deposit (car only): 0, one or two days, 100,000 FCFA at most. */
  caution: number;
  caution_jours: 0 | 1 | 2;
}

export interface LieuRemise {
  id: number;
  nom: string;
  ville: string;
  adresse_requise: boolean;
  frais: number;
  fuseau: string;
}

export interface TarifsChauffeur {
  prix_jour: number;
  prime_hors_lome: number;
  prime_hors_pays: number;
  heure_sup: number;
}

export interface CatalogueLocation {
  active: boolean;
  regles?: {
    delai_min_jours: number; duree_max_jours: number; annulation_gratuite_heures: number; conditions: string;
    caution_en_ligne: boolean; restitution_caution_heures: number;
  };
  categories?: CategorieVehicule[];
  chauffeur?: TarifsChauffeur;
  lieux?: LieuRemise[];
  filtres?: { gammes: { code: string; nom: string }[]; boites: { code: string; nom: string }[]; carburants: { code: string; nom: string }[] };
}

export interface DevisLocation {
  jours: number;
  prix_jour: number;
  prix_vehicule: number;
  frais_lieux: number;
  /** 7,000 FCFA per day for the options with a driver. */
  prix_chauffeur: number;
  /** Driver's travel allowances (outside Lomé, outside the country). */
  primes: number;
  prix: number;
  caution: number;
  /** Deposit paid with the rental and kept by Kwa-Ba (otherwise paid to the owner at handover). */
  caution_en_ligne: boolean;
  /** Amount paid online: the rental and, where applicable, the deposit. */
  a_payer: number;
}

export interface Location {
  id: string;
  reference: string;
  libelle: string;
  categorie: number | null;
  /** null for a driver alone (customer's vehicle). */
  categorie_detail: CategorieVehicule | null;
  formule: Formule;
  lieu_prise_detail: LieuRemise;
  adresse_prise: string;
  lieu_retour_detail: LieuRemise;
  adresse_retour: string;
  debut_locale: string;
  fin_locale: string;
  passagers: number;
  telephone: string;
  precisions: string;
  conducteur: string;
  jours: number;
  prix_jour: number;
  frais_lieux: number;
  prix_chauffeur: number;
  primes: number;
  jours_hors_lome: number;
  jours_hors_pays: number;
  chauffeur_demande: number | null;
  prix: number;
  caution: number;
  caution_en_ligne: boolean;
  a_payer: number;
  /** Deposit kept by Kwa-Ba: refunded `restitution_heures` after the return, minus the withheld amount. */
  caution_etat: { restituee: boolean; retenue: number; motif: string; restitution_heures: number } | null;
  statut: StatutLocation;
  expire_le: string | null;
  annulee_par: string;
  /** Assigned vehicle; the owner and the driver are never shown (contact details sent by email). */
  vehicule_attribue: { vehicule: string; immatriculation: string } | null;
  paiement: "en_attente" | "reussi" | "echoue" | "annule" | null;
  remboursement: { montant: number; statut: "attente_numero" | "en_cours" | "envoye" } | null;
  annulation_gratuite: boolean;
  /** Amount given back if the traveller cancels now (null if cancelling is no longer possible). */
  rembourse_si_annulation: number | null;
  cree_le: string;
}

/** "My driver": a driver who has already driven the traveller. */
export interface MonChauffeur {
  id: number;
  nom: string;
}
