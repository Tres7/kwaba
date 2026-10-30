const isDev = process.env.NODE_ENV !== "production";

/** Receives the browsers' violation reports (app/api/csp-report, with an exact location in nginx). */
export const RAPPORTS_CSP = "/api/csp-report";

/** Public origin of the API, which serves the uploaded photos (baked at build time, like NEXT_PUBLIC_API_URL). */
function apiOrigin(): string {
  try {
    return new URL(process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api").origin;
  } catch {
    return "";
  }
}

/**
 * Content security policy: the browser only loads what comes from these origins. Limits the impact of an XSS flaw (no
 * injected script, no data sent to an unknown server).
 *
 * With a nonce (pages, middleware.ts): only the scripts carrying the nonce of this response run, then the ones they load
 * themselves ('strict-dynamic': Next.js chunks, Google sign-in, Turnstile). Current browsers ignore 'self', the hosts and
 * 'unsafe-inline' next to these two, which only remain for older browsers.
 * Without a nonce (/api/, next.config.ts): those answers are data, no inline script has to run.
 */
export function politiqueCsp(nonce?: string): string {
  const scripts = nonce
    ? `'nonce-${nonce}' 'strict-dynamic' 'self' 'unsafe-inline' https://accounts.google.com/gsi/client https://challenges.cloudflare.com`
    : "'self'";
  return [
    "default-src 'self'",
    `script-src ${scripts}${isDev ? " 'unsafe-eval'" : ""}`,
    // Inline styles remain allowed (next-themes, sonner, style props): a nonce here would disable 'unsafe-inline'
    "style-src 'self' 'unsafe-inline' https://accounts.google.com/gsi/style",
    // Photos: site and API (R2 storage is served under /photos/), Google avatars, Unsplash (backgrounds in the code and
    // seeded experiences). Same hosts as IMAGES_HOTES_AUTORISES on the API. Never "https:": a script could send data to
    // any site through the address of an image.
    `img-src 'self' data: blob: ${apiOrigin()} https://*.googleusercontent.com https://images.unsplash.com${isDev ? " http: https:" : ""}`,
    "font-src 'self' data:",
    // The browser only calls the site: the API is reached through the Next.js server (app/api/proxy)
    `connect-src 'self' https://accounts.google.com${isDev ? " ws:" : ""}`,
    "frame-src https://accounts.google.com https://maps.google.com https://www.google.com https://challenges.cloudflare.com",
    "frame-ancestors 'none'",
    "object-src 'none'",
    "base-uri 'self'",
    // Payments (FedaPay, PayPal) go through redirects, not forms: only the site itself receives
    "form-action 'self'",
    ...(isDev ? [] : ["upgrade-insecure-requests"]),
    // report-to for Chromium, report-uri for Firefox and Safari. Named in Reporting-Endpoints (next.config.ts).
    ...(nonce ? [`report-uri ${RAPPORTS_CSP}`, "report-to csp"] : []),
  ].join("; ");
}
