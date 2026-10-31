export interface CarteLogement {
  type: "logement";
  id: string;
  nom: string;
  ville: string;
  quartier: string;
  image: string;
  prix_nuit: number;
  note: number;
  nb_avis: number;
  capacite: number;
  arrivee: string | null;
  depart: string | null;
  voyageurs: number | null;
  total: number | null;
  nuits: number | null;
}

export interface CarteTransfert {
  type: "transfert";
  aeroport: string;
  ville: string;
  /** Ticket time, YYYY-MM-DDTHH:MM. */
  arrivee: string;
  passagers: number;
  bagages: number;
  trop_tard: boolean;
  options: { categorie: string; nom: string; prix: number; disponible: boolean }[];
}

export interface CarteTogether {
  type: "together";
  nom: string;
  destination: string;
  arrivee: string | null;
  depart: string | null;
  voyageurs: number;
  logements: { id: string; nom: string }[];
}

export type Carte = CarteLogement | CarteTransfert | CarteTogether;

export interface MessageConcierge {
  id: number | string;
  role: "user" | "assistant";
  texte: string;
  cartes: Carte[];
}

export interface ConversationResume {
  id: string;
  titre: string;
  mis_a_jour_le: string;
}
