import type { HebergementType } from "@/types/api/models";

/** Props of the tabs of a trip. */
export interface SectionVoyage {
  v: Voyage;
  appliquer: (d: Voyage) => void;
  recharger: () => void;
}

export interface VoyageResume {
  id: string;
  nom: string;
  destination: string;
  date_debut: string | null;
  date_fin: string | null;
  nb_membres: number;
  nb_propositions: number;
  organisateur: string;
  est_organisateur: boolean;
}

export interface BudgetLogement {
  nuits: number;
  total: number;
  par_personne: number;
  personnes: number;
}

export interface Proposition {
  id: number;
  commentaire: string;
  propose_par: string;
  peut_supprimer: boolean;
  votes: number;
  votants: string[];
  hebergement: {
    id: string;
    name: string;
    city: string;
    location: string;
    type: HebergementType;
    image_url: string;
    price_per_night: number;
    max_guests: number;
    rating: number;
    review_count: number;
  };
  budget: BudgetLogement | null;
  /** null if the trip has no dates yet. */
  disponible: boolean | null;
  assez_grand: boolean;
}

export interface Etape {
  id: number;
  date: string;
  heure: string | null;
  titre: string;
  lieu: string;
  details: string;
  ajoute_par: string;
  peut_supprimer: boolean;
}

export interface ReservationPartagee {
  id: number;
  reservation_id: string;
  reference: string;
  hebergement: string;
  hebergement_id: string;
  ville: string;
  adresse: string;
  check_in: string;
  check_out: string;
  voyageurs: number;
  statut: "pending" | "confirmed" | "cancelled";
  total: number;
  reserve_par: string;
  peut_retirer: boolean;
}

export interface Voyage {
  id: string;
  nom: string;
  destination: string;
  date_debut: string | null;
  date_fin: string | null;
  nuits: number | null;
  nb_voyageurs: number;
  notes: string;
  organisateur: string;
  est_organisateur: boolean;
  code_invitation: string;
  membres: { id: string; nom: string; organisateur: boolean; moi: boolean }[];
  propositions: Proposition[];
  mon_vote: number | null;
  proposition_retenue: number | null;
  etapes: Etape[];
  reservations: ReservationPartagee[];
  mis_a_jour_le: string;
}

export interface ApercuInvitation {
  id: string;
  nom: string;
  destination: string;
  date_debut: string | null;
  date_fin: string | null;
  organisateur: string;
  nb_membres: number;
  deja_membre: boolean;
}
