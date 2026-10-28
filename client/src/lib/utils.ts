import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Traveller's service fees (terms of sale, art. 6.4); the listing gives the visitor's exact rate (3 % for loyal customers). */
export const SERVICE_FEE_RATE = 0.06;

export const FALLBACK_IMAGE =
  "https://images.unsplash.com/photo-1542314831-c6a4d27ce6a2?q=80&w=1200&auto=format&fit=crop";

// Display language of dates, prices and labels: set at every render by <SynchroLangue /> (site root)
let langueCourante: "fr" | "en" = "fr";
const LOCALES = { fr: "fr-FR", en: "en-GB" } as const;

export function definirLangue(langue: string) {
  langueCourante = langue === "en" ? "en" : "fr";
}

export function langue(): "fr" | "en" {
  return langueCourante;
}

/** Picks the text of the current language: selon({ fr: "…", en: "…" }). */
export function selon<T>(textes: { fr: T; en: T }): T {
  return textes[langueCourante];
}

const TYPES: Record<string, { fr: string; en: string }> = {
  hotel: { fr: "Hôtel", en: "Hotel" },
  villa: { fr: "Villa", en: "Villa" },
  maison: { fr: "Maison", en: "House" },
  appartement: { fr: "Appartement", en: "Apartment" },
  residence: { fr: "Résidence hôtelière", en: "Aparthotel" },
  auberge: { fr: "Auberge", en: "Guesthouse" },
};

/**
 * Labels of the listing types, in the current language (TYPE_LABELS[type]).
 * The Proxy's target is the table itself: Object.keys(TYPE_LABELS) lists the types. On an empty object, the list
 * would be empty and the type choice would disappear from the host's form.
 */
export const TYPE_LABELS: Record<string, string> = new Proxy(TYPES as unknown as Record<string, string>, {
  get: (_, type: string) => (TYPES[type] ? TYPES[type][langueCourante] : type),
});

const ROLES: Record<string, { fr: string; en: string }> = {
  voyageur: { fr: "Voyageur", en: "Traveller" },
  hote: { fr: "Hôte", en: "Host" },
  admin: { fr: "Administrateur", en: "Administrator" },
  agent: { fr: "Agent de terrain", en: "Field agent" },
};

/** Role labels, in the current language (ROLE_LABELS[role]). */
export const ROLE_LABELS: Record<string, string> = new Proxy(ROLES as unknown as Record<string, string>, {
  get: (_, role: string) => (ROLES[role] ? ROLES[role][langueCourante] : role),
});

/** Label of a listing type in a given language (server side, where there is no current language). */
export function libelleType(type: string, locale: "fr" | "en"): string {
  return TYPES[type]?.[locale] ?? type;
}

// Display currency of prices, chosen by the visitor (<DeviseProvider />). Payments stay in FCFA.
export type Devise = "XOF" | "EUR";
/** Fixed parity of the CFA franc (WAEMU): 1 € = 655.957 FCFA. */
export const FCFA_PAR_EURO = 655.957;
let deviseCourante: Devise = "XOF";

export function definirDevise(devise: Devise) {
  deviseCourante = devise;
}

export function devise(): Devise {
  return deviseCourante;
}

// fr-FR separates thousands with a narrow space (U+202F) almost invisible in some fonts:
// it is replaced with a regular non-breaking space (U+00A0)
const espaces = (texte: string) => texte.replace(/\u202f/g, "\u00a0");

/** Amount in FCFA whatever the chosen currency: charged amounts, payment buttons. */
export function formatFcfa(price: number | string): string {
  return `${espaces(Math.round(Number(price)).toLocaleString(LOCALES[langueCourante]))}\u00a0FCFA`;
}

/** Prices stored in FCFA, displayed in the currency chosen by the visitor (euros rounded to the unit from 10 €). */
export function formatPrice(price: number | string): string {
  if (deviseCourante === "XOF") return formatFcfa(price);
  const euros = Number(price) / FCFA_PAR_EURO;
  const decimales = euros < 10 ? 2 : 0;
  return espaces(euros.toLocaleString(LOCALES[langueCourante], {
    style: "currency", currency: "EUR", minimumFractionDigits: decimales, maximumFractionDigits: decimales,
  }));
}

export function calculateNights(checkIn: string, checkOut: string): number {
  if (!checkIn || !checkOut) return 0;
  const diff = new Date(checkOut).getTime() - new Date(checkIn).getTime();
  return Math.max(0, Math.round(diff / (1000 * 60 * 60 * 24)));
}

export function calculateServiceFee(subtotal: number, rate = SERVICE_FEE_RATE): number {
  return Math.round(subtotal * rate);
}

/**
 * Price of a night for the traveller, service fees included (100,000 FCFA at 6 %: 106,000 FCFA). Preview computed
 * separately, without touching the host's price; same rounding to the franc as the server (apps/paiements/tarifs.py),
 * which always computes the final amount again.
 */
export function prixNuitFraisInclus(prixParNuit: number, rate = SERVICE_FEE_RATE): { frais: number; total: number } {
  const frais = calculateServiceFee(prixParNuit, rate);
  return { frais, total: prixParNuit + frais };
}

export function formatDate(d: string, opts: Intl.DateTimeFormatOptions = { day: "numeric", month: "short", year: "numeric" }) {
  if (!d) return "-";
  return new Date(d).toLocaleDateString(LOCALES[langueCourante], opts);
}

/** Local date in YYYY-MM-DD format (avoids the UTC shift of toISOString). */
export function isoDate(date: Date = new Date()): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

export function addDays(iso: string, days: number): string {
  const d = new Date(`${iso}T00:00:00`);
  d.setDate(d.getDate() + days);
  return isoDate(d);
}

export function initials(name?: string | null): string {
  if (!name) return "U";
  return name
    .split(" ")
    .filter(Boolean)
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
}
