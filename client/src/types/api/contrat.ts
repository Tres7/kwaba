export type TypeContrat = "hote" | "hotel" | "loueur" | "chauffeur" | "ong";
export type StatutContrat = "a_signer" | "signe" | "annule";

export interface BlocContrat {
  type: "titre" | "texte";
  texte: string;
}

/** Contract as seen by the signer (personal link or host space). */
export interface ContratPublic {
  reference: string | null;
  titre: string;
  type: TypeContrat;
  type_libelle: string;
  statut: StatutContrat;
  partie_nom: string;
  kwaba_signataire: string;
  version: number;
  blocs: BlocContrat[];
  expire_le: string | null;
  expire: boolean;
  signe_le: string | null;
  signataire_nom: string;
}

export interface SignatureContrat {
  nom: string;
  signature: string;
  accepte: boolean;
}

/** Pre-launch pre-registration of the connected host (GET /v1/contrats/preinscription/). */
export interface Preinscription {
  requise: boolean;
  acceptee: boolean;
  version: number;
  langue: "fr" | "en";
  texte: string;
}
