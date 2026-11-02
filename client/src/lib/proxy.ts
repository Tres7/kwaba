/** Rules of the API proxy (app/api/proxy): what a request of the browser may reach and what crosses over. */

const METHODES_SURES = ["GET", "HEAD", "OPTIONS"];

// What the API needs from the browser's request. Never the cookies: they hold the session of the site.
// X-Forwarded-For: chain received from nginx, otherwise every visitor would have the address of this server.
const ENTETES_REQUETE = ["accept", "accept-language", "content-type", "content-length", "x-forwarded-for"];

// Specific to the connection between the two servers, or managed by nginx for the whole site
const ENTETES_REPONSE_RETIREES = ["connection", "keep-alive", "transfer-encoding", "set-cookie", "server", "strict-transport-security"];

/** Path of the API route asked for, null if it is not allowed: only /v1/… and nothing that could leave that folder. */
export function cheminApi(segments: string[]): string | null {
  if (segments[0] !== "v1" || segments.length < 2) return null;
  if (segments.some((s) => !s || s === "." || s === ".." || s.includes("/") || s.includes("\\"))) return null;
  return `${segments.map(encodeURIComponent).join("/")}/`;
}

/**
 * The browser adds the session cookie itself, unlike the Bearer token used before: a request that changes something must
 * come from the site. SameSite=Lax already covers other sites; this check also covers subdomains.
 */
export function origineAutorisee(methode: string, origine: string | null, hote: string | null): boolean {
  if (METHODES_SURES.includes(methode)) return true;
  if (!origine || !hote) return false;
  try {
    return new URL(origine).hostname === hote.split(":")[0];
  } catch {
    return false;
  }
}

/**
 * Headers sent to the API. `apiPublique`: address of the API as seen from the outside. The API builds absolute addresses
 * from it (uploaded photos), which would otherwise point to the internal network. X-Forwarded-Host and not Host, which
 * fetch ignores: see USE_X_FORWARDED_HOST in the API settings.
 */
export function entetesVersApi(recus: Headers, accessToken: string | undefined, apiPublique: URL): Headers {
  const entetes = new Headers({
    "x-forwarded-host": apiPublique.host,
    "x-forwarded-proto": apiPublique.protocol.replace(":", ""),
    // Stays readable by the browser as it is: Next.js and nginx compress for the visitor
    "accept-encoding": "identity",
  });
  for (const nom of ENTETES_REQUETE) {
    const valeur = recus.get(nom);
    if (valeur) entetes.set(nom, valeur);
  }
  if (accessToken) entetes.set("authorization", `Bearer ${accessToken}`);
  return entetes;
}

export function entetesVersNavigateur(recus: Headers): Headers {
  const entetes = new Headers(recus);
  for (const nom of ENTETES_REPONSE_RETIREES) entetes.delete(nom);
  return entetes;
}
