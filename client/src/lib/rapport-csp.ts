/** CSP violation kept for the logs: nothing else from the report, which anyone can send. */
export type ViolationCsp = {
  page: string;
  directive: string;
  bloque: string;
  source: string;
  ligne: number | null;
};

const TAILLE_CHAMP = 200;

const texte = (valeur: unknown) => (typeof valeur === "string" ? valeur.slice(0, TAILLE_CHAMP) : "");

/**
 * Address without query string nor fragment (they can hold an email or a token), nor the token of a signature link, which
 * gives access to the contract. "inline" or "eval" stay as they are.
 */
function sansRequete(valeur: unknown): string {
  const adresse = texte(valeur);
  let chemin: string;
  try {
    const { origin, pathname } = new URL(adresse);
    chemin = origin === "null" ? adresse.split(/[?#]/)[0] : `${origin}${pathname}`;
  } catch {
    chemin = adresse.split(/[?#]/)[0];
  }
  return chemin.replace(/(\/(?:contrat|contrats\/signature)\/)[^/]+/, "$1***");
}

function violation(page: unknown, directive: unknown, bloque: unknown, source: unknown, ligne: unknown): ViolationCsp {
  return {
    page: sansRequete(page),
    directive: texte(directive),
    bloque: sansRequete(bloque),
    source: sansRequete(source),
    ligne: typeof ligne === "number" ? ligne : null,
  };
}

/**
 * Reads the two report formats: {"csp-report": {…}} (report-uri: Firefox, Safari) and [{type: "csp-violation", body: {…}}]
 * (report-to: Chromium). Anything else gives an empty list.
 */
export function lireRapportsCsp(corps: unknown): ViolationCsp[] {
  if (Array.isArray(corps)) {
    return corps
      .filter((r) => r?.type === "csp-violation" && r.body && typeof r.body === "object")
      .map(({ body }) => violation(body.documentURL, body.effectiveDirective, body.blockedURL, body.sourceFile, body.lineNumber));
  }
  const rapport = (corps as { "csp-report"?: Record<string, unknown> } | null)?.["csp-report"];
  if (!rapport || typeof rapport !== "object") return [];
  return [violation(rapport["document-uri"], rapport["effective-directive"] ?? rapport["violated-directive"], rapport["blocked-uri"], rapport["source-file"], rapport["line-number"])];
}
