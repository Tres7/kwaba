import api from "@/lib/api";
import type { ResultatVerification } from "./types";

/** Mistakes of a text; `langue`: language of the site, used when the text does not tell its own. */
export async function verifierTexte(texte: string, langue: string, signal?: AbortSignal) {
  return (await api.post<ResultatVerification>("/v1/correcteur/verifier/", { texte, langue }, { signal })).data;
}
