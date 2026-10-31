import type { MoyenPaiement, StatutPaiement } from "@/types/api/paiement";

export interface Aeroport {
  code: string;
  nom: string;
  ville: string;
  pays: string;
  fuseau: string;
  /** Price of each vehicle from this airport (same price by day and by night). */
  prix: Partial<Record<CategorieVehicule, number>>;
}

export type CategorieVehicule = "berline" | "confort" | "van";

export interface Vehicule {
  nom: string;
  description: string;
  passagers: number;
  bagages: number;
}

export interface OptionDevis extends Vehicule {
  categorie: CategorieVehicule;
  prix: number;
  disponible: boolean;
  motif: string;
}

export interface Devis {
  options: OptionDevis[];
  trop_tard: boolean;
  delai_min_heures: number;
  attente_incluse_minutes: number;
}

export type StatutTransfert = "en_attente_paiement" | "confirme" | "chauffeur_assigne" | "termine" | "annule";

export interface Transfert {
  id: string;
  reference: string;
  aeroport: string;
  aeroport_detail: Aeroport;
  arrivee: string;
  /** Ticket time, in the airport's time zone (YYYY-MM-DDTHH:MM). */
  arrivee_locale: string;
  numero_vol: string;
  passagers: number;
  bagages: number;
  categorie: CategorieVehicule;
  vehicule: Vehicule;
  destination: string;
  telephone: string;
  message: string;
  reservation: string | null;
  prix: number;
  majoration_nuit: boolean;
  moyen: MoyenPaiement;
  statut: StatutTransfert;
  expire_le: string | null;
  annule_par: "" | "voyageur" | "plateforme" | "expiration";
  chauffeur: { nom: string; telephone: string; vehicule: string; immatriculation: string } | null;
  paiement: StatutPaiement | null;
  remboursement: { montant: number; statut: "attente_numero" | "en_cours" | "envoye" } | null;
  annulation_gratuite: boolean;
  cree_le: string;
}
