/**
 * Audience measurement (Google Analytics), only after consent (lib/consentement.ts): before that, no script and no cookie.
 *
 * Google receives the path of the page without its query string (password resets and payment returns carry tokens
 * there), and without the identifier of a private page. Advertising features stay off. The team's pages are not measured.
 */
declare global {
  interface Window {
    dataLayer?: unknown[];
    gtag?: (...args: unknown[]) => void;
  }
}

const DUREE_COOKIES_S = 395 * 24 * 60 * 60; // 13 months, the limit advised by the CNIL

const PAGES_EQUIPE = /^\/(backoffice|agent)(\/|$)/;

// Pages with an identifier in their address, which may be a secret (contract link, group invitation). Listing and
// project pages are public and keep theirs. A new dynamic page must be added here: mesure-audience.test.ts checks them all.
const PAGES_PRIVEES =
  /^((?:\/en)?\/(?:contrat|give\/don|hote\/espace\/calendrier|hote\/espace\/types|location|messages|profil\/reservations|reservation(?:\/confirmation|\/paiement)?|together(?:\/rejoindre)?|transfert))\/[^/]+/;

/** Path sent to Google, null when the page is not measured. */
export function cheminMesurable(chemin: string): string | null {
  if (PAGES_EQUIPE.test(chemin)) return null;
  return chemin.replace(PAGES_PRIVEES, "$1/:id");
}

function provenance(): string {
  try {
    const url = new URL(document.referrer);
    if (url.origin !== window.location.origin) return url.origin;
    return `${url.origin}${cheminMesurable(url.pathname) ?? ""}`;
  } catch {
    return "";
  }
}

function drapeauCoupure(id: string) {
  return `ga-disable-${id}` as keyof Window;
}

export function activerMesure(id: string) {
  (window as unknown as Record<string, boolean>)[drapeauCoupure(id)] = false;
  if (window.gtag) return;
  window.dataLayer = window.dataLayer ?? [];
  window.gtag = function gtag() {
    // eslint-disable-next-line prefer-rest-params -- gtag.js only reads the arguments object, not an array
    window.dataLayer?.push(arguments);
  };
  window.gtag("consent", "default", {
    analytics_storage: "granted",
    ad_storage: "denied",
    ad_user_data: "denied",
    ad_personalization: "denied",
  });
  window.gtag("js", new Date());
  window.gtag("config", id, {
    send_page_view: false, // mesurerPage sends them, with the cleaned address
    allow_google_signals: false,
    allow_ad_personalization_signals: false,
    cookie_expires: DUREE_COOKIES_S,
  });
  const script = document.createElement("script");
  script.async = true;
  script.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(id)}`;
  document.head.appendChild(script);
}

export function mesurerPage(chemin: string) {
  const page = cheminMesurable(chemin);
  if (!page || !window.gtag) return;
  // "set" also covers Google's automatic events (scrolling, outbound links), which would otherwise read the address bar
  window.gtag("set", { page_location: `${window.location.origin}${page}`, page_referrer: provenance() });
  window.gtag("event", "page_view");
}

/** Consent refused or withdrawn: nothing more leaves, and the Google Analytics cookies are removed. */
export function couperMesure(id: string) {
  (window as unknown as Record<string, boolean>)[drapeauCoupure(id)] = true;
  const parties = window.location.hostname.split(".");
  // Google sets its cookies on the widest possible domain
  const domaines = parties.map((_, i) => parties.slice(i).join(".")).filter((d) => d.includes("."));
  const noms = document.cookie.split("; ").map((c) => c.split("=")[0]).filter((nom) => nom.startsWith("_ga"));
  for (const nom of noms) {
    document.cookie = `${nom}=; Max-Age=0; path=/`;
    for (const domaine of domaines) document.cookie = `${nom}=; Max-Age=0; path=/; domain=${domaine}`;
  }
}
