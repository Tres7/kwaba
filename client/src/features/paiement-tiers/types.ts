/** Payment of a stay by a third party: the traveller asks someone else to pay their booking in full. */

/** State of the traveller's request. `lien`: given only when it is created (only its fingerprint is kept). */
export interface DemandeTiers {
  active: boolean;
  expire_le: string | null;
  /** Also open to the members of a Together trip. */
  groupe: boolean;
  lien?: string;
}

/** What the payer sees: the stay and its price, the traveller's first name. Neither address nor contact details. */
export interface ApercuTiers {
  demande: string;
  reference: string;
  voyageur: string;
  hebergement: { name: string; city: string; image_url: string; type: string };
  check_in: string;
  check_out: string;
  nuits: number;
  voyageurs: number;
  total: number;
  expire_le: string;
  /** False with `motif`: why this person cannot pay it (link expired, own booking, dates taken…). */
  payable: boolean;
  motif: string;
}

export interface StatutTiers {
  reservation: "pending" | "confirmed" | "cancelled";
  paiement: "en_attente" | "reussi" | "echoue" | "annule" | null;
  voyageur: string;
}
