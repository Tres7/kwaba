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

/** Address of an API route for the browser, for the calls that cannot go through axios (Concierge SSE stream, sign-up…). */
export function urlProxy(chemin: string) {
  return `${PROXY_API}${sansSlashFinal(chemin)}`;
}
