/**
 * Consent to cookies and third-party content (GDPR / CNIL recommendations).
 *
 * Only non-essential trackers require consent. Today, a single category:
 * third-party content (Google Maps map), which may set its own cookies.
 * Sign-in and security cookies (NextAuth) are strictly necessary: no consent.
 */
export interface Consentement {
  version: number;
  /** ISO date of the choice (proof and validity period). */
  date: string;
  contenusTiers: boolean;
}

// To increase when a new category or a new third-party service is added: the choice is asked again
export const VERSION_CONSENTEMENT = 1;
const CLE = "kwaba_consentement";
// Key used before the AfriStay → Kwa-Ba rename: its choice is carried over once (original date kept), then removed
const ANCIENNE_CLE = "afristay_consentement";
// The CNIL recommends asking for the choice again after 6 months
const DUREE_MS = 182 * 24 * 60 * 60 * 1000;
export const EVENEMENT = "kwaba:consentement";

function lireBrut(): string | null {
  const brut = window.localStorage.getItem(CLE);
  if (brut) return brut;
  const ancien = window.localStorage.getItem(ANCIENNE_CLE);
  if (ancien) {
    window.localStorage.setItem(CLE, ancien);
    window.localStorage.removeItem(ANCIENNE_CLE);
  }
  return ancien;
}

export function lireConsentement(): Consentement | null {
  try {
    const brut = lireBrut();
    if (!brut) return null;
    const c = JSON.parse(brut) as Consentement;
    if (c.version !== VERSION_CONSENTEMENT) return null;
    if (Date.now() - new Date(c.date).getTime() > DUREE_MS) return null;
    return c;
  } catch {
    return null;
  }
}

export function enregistrerConsentement(contenusTiers: boolean): Consentement {
  const c: Consentement = { version: VERSION_CONSENTEMENT, date: new Date().toISOString(), contenusTiers };
  try {
    window.localStorage.setItem(CLE, JSON.stringify(c));
    window.localStorage.removeItem(ANCIENNE_CLE);
  } catch {
    // Storage unavailable (strict private browsing): the choice applies to the current page
  }
  window.dispatchEvent(new CustomEvent(EVENEMENT, { detail: c }));
  return c;
}
