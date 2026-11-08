/** Route of the Next.js server that relays the browser's API calls and adds the session's token (app/api/proxy). */
export const PROXY_API = "/api/proxy";

/** API address for the code that runs on the Next.js server. */
export function getApiBaseUrl() {
  return process.env.INTERNAL_API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
}

/** Without the final slash, which Next.js would answer with a redirect: the proxy puts it back for Django. */
export function sansSlashFinal(url: string) {
  const [chemin, ...requete] = url.split("?");
  return [chemin.replace(/\/$/, ""), ...requete].join("?");
}

/**
 * True when the path has a segment "." or "..", also written %2e or behind a backslash (read as "/"): the browser
 * would resolve it and leave the API route asked for. An id taken from the page's address ("../../admin/…") could
 * otherwise send the visitor's request, with their session, to another route of the API.
 */
export function sortDuChemin(url: string): boolean {
  const chemin = url.split(/[?#]/)[0];
  return chemin.split(/[\\/]/).some((s) => {
    const segment = s.toLowerCase().replaceAll("%2e", ".");
    return segment === "." || segment === "..";
  });
}

export class CheminRefuse extends Error {
  constructor(url: string) {
    super(`Adresse d'API refusée : ${url}`);
  }
}

/** Address of an API route for the browser, for the calls that cannot go through axios (Concierge SSE stream, sign-up…). */
export function urlProxy(chemin: string) {
  if (sortDuChemin(chemin)) throw new CheminRefuse(chemin);
  return `${PROXY_API}${sansSlashFinal(chemin)}`;
}
