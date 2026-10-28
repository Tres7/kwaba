export type HebergementType = "hotel" | "villa" | "maison" | "appartement" | "residence" | "auberge";
export type PolitiqueAnnulation = "souple" | "moderee" | "ferme";

/** What a traveller books in an establishment: a unit type and its stock (a hotel's "Double standard", a house). */
export interface TypeLogement {
  id: string;
  nom: string;
  description: string;
  /** Guests per unit. */
  capacite: number;
  prix_nuit: number;
  /** Number of identical units. */
  quantite: number;
  photos: string[];
}

/** Availability over the searched dates (search with dates only). */
export interface DisponibiliteRecherche {
  disponible: boolean;
  /** Units still bookable over the whole stay, all types together. */
  unites_restantes: number;
  unites_total: number;
  /** Full: first arrival date for a stay of the same length (null if none within 60 days). */
  prochaine_date: string | null;
}

export interface Hebergement {
  id: string;
  name: string;
  description: string;
  type: HebergementType;
  city: string;
  location: string;
  price_per_night: number;
  rating: number;
  review_count: number;
  image_url: string;
  images: string[];
  max_guests: number;
  amenities: string[];
  is_available: boolean;
  /** Details (null for listings published before they were added) */
  surface_m2: number | null;
  chambres: number | null;
  salles_de_bain: number | null;
  lits_doubles: number;
  lits_simples: number;
  canapes_lits: number;
  petit_dejeuner: "" | "non" | "inclus" | "option";
  petit_dejeuner_prix: number | null;
  arrivee_a_partir: string | null;
  depart_avant: string | null;
  /** Cancellation policy chosen by the host (terms of sale, appendix 1). */
  politique_annulation: PolitiqueAnnulation;
  /** Service fee rate for this visitor: 0.06, or 0.03 if they come back to this host (loyal customer). */
  frais_voyageur: number;
  /** Verification by a field agent: only "verifiee" listings are public */
  statut_verification: "en_attente" | "verifiee" | "refusee";
  verifiee_le: string | null;
  /** Agent's refusal reason: filled in only for the listing's host */
  motif_refus: string;
  /** Owner only: actually public (verified, not hidden, opening done, host agreement signed). null for others. */
  en_ligne?: boolean | null;
  host_id: string;
  host_name: string;
  /** The host's identity document checked by Kwa-Ba ("Verified host" badge). */
  hote_verifie?: boolean;
  is_favorite: boolean;
  /** Inspection visit validated by Kwa-Ba (missing while the backend does not expose it). */
  est_verifie?: boolean;
  created_at: string;
  /** Unit types to choose from: listing page only (null in lists). */
  types?: TypeLogement[] | null;
  /** Search with dates only (null otherwise). */
  disponibilite?: DisponibiliteRecherche | null;
}

export interface City {
  city: string;
  count: number;
  min_price: number;
  image_url: string;
}

export type ReservationStatus = "pending" | "confirmed" | "cancelled";

export interface Reservation {
  id: string;
  hebergement: string;
  hebergement_detail: Hebergement;
  type_logement: string | null;
  type_logement_nom: string | null;
  nb_unites: number;
  check_in: string;
  check_out: string;
  guests_count: number;
  total_price: number;
  status: ReservationStatus;
  payment_method: "mobile_money" | "carte" | "paypal";
  message: string;
  nights: number;
  reference: string;
  guest_name: string;
  avis_id: string | null;
  peut_evaluer: boolean;
  created_at: string;
  montants: {
    prix_nuits: number;
    frais_service: number;
    /** Service fee rate in % (6, or 3 for loyal customers). */
    taux_frais: number;
    total: number;
    commission_hote: number;
    montant_hote: number;
  };
  /** Last online payment: null if the booking was made without online payment. */
  paiement: "en_attente" | "reussi" | "echoue" | "annule" | null;
  /** attente_numero: the traveller must give their Mobile Money account to be refunded. */
  remboursement: { montant: number; statut: "attente_numero" | "en_cours" | "envoye" } | null;
  /** End of the payment period (booking waiting for payment). */
  expire_le: string | null;
  annule_par: "" | "voyageur" | "hote" | "plateforme" | "expiration";
}

export interface Favori {
  id: string;
  hebergement: string;
  hebergement_detail: Hebergement;
  created_at: string;
}

export interface Paginated<T> {
  results: T[];
  count: number;
}

export interface Me {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: "voyageur" | "hote" | "agent" | "admin";
  phone: string | null;
  avatar_url: string | null;
  is_verified: boolean;
  is_active: boolean;
  date_joined: string;
}

export type CritereAvis = "proprete" | "conformite" | "communication" | "emplacement" | "qualite_prix";

export interface Avis {
  id: string;
  note: number;
  criteres: Record<CritereAvis, number>;
  commentaire: string;
  auteur: { prenom: string; initiale: string; avatar_url: string | null };
  sejour: string;
  reponse_hote: string;
  reponse_le: string | null;
  created_at: string;
}

export interface AvisResume {
  moyenne: number | null;
  total: number;
  criteres: Record<CritereAvis, number | null>;
  libelles: Record<CritereAvis, string>;
  repartition: Record<string, number>;
}

export interface AvisPage {
  resume: AvisResume;
  results: Avis[];
  count: number;
}

export interface SejourAEvaluer {
  reservation_id: string;
  check_in: string;
  check_out: string;
  hebergement: Hebergement;
}
