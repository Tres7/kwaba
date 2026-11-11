export type TypeFaute = "orthographe" | "grammaire";

/** Mistake found by the checker (apps/correcteur of the API). */
export interface Faute {
  /** Position in UTF-16 units, like the indexes of a JavaScript string */
  debut: number;
  longueur: number;
  /** Text of the mistake, as it was when it was checked */
  extrait: string;
  type: TypeFaute;
  message: string;
  /** Corrections, the most likely first; can be empty */
  remplacements: string[];
  regle: string;
}

export interface ResultatVerification {
  /** false: the checker cannot answer (the field works without it) */
  disponible: boolean;
  fautes: Faute[];
}
