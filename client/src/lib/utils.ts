import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Traveller's service fees (terms of sale, art. 6.4); the listing gives the visitor's exact rate (3 % for loyal customers). */
export const SERVICE_FEE_RATE = 0.06;

/** Listing without a photo: neutral drawing served by the site (a stock photo would pass for the place itself). */
export const FALLBACK_IMAGE = "/brand/logement-sans-photo.svg";

// Language of what runs outside rendering (event handlers, API errors) and of the French-only spaces, set by
// <SynchroLangue />. Everything rendered uses useFormat (lib/format.ts), which reads the language of the page.
let langueCourante: "fr" | "en" = "fr";
const LOCALES = { fr: "fr-FR", en: "en-GB" } as const;

export function definirLangue(langue: string) {
  // Browser only: on the server, this variable would be shared by all the requests being rendered
  if (typeof window !== "undefined") langueCourante = langue === "en" ? "en" : "fr";
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
 * Labels of a table in a language (libelles[code]).
 * The Proxy's target is the table itself: Object.keys(TYPE_LABELS) lists the types. On an empty object, the list
 * would be empty and the type choice would disappear from the host's form.
 */
function libelles(table: Record<string, { fr: string; en: string }>, langue: "fr" | "en"): Record<string, string> {
  return new Proxy(table as unknown as Record<string, string>, {
    get: (_, code: string) => (table[code] ? table[code][langue] : code),
  });
}

const ROLES: Record<string, { fr: string; en: string }> = {
  voyageur: { fr: "Voyageur", en: "Traveller" },
  hote: { fr: "Hôte", en: "Host" },
  admin: { fr: "Administrateur", en: "Administrator" },
  agent: { fr: "Agent de terrain", en: "Field agent" },
};

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

function creerFormats(langueFormat: "fr" | "en") {
  const locale = LOCALES[langueFormat];

  /** Amount in FCFA whatever the chosen currency: charged amounts, payment buttons. */
  const formatFcfa = (price: number | string) => `${espaces(Math.round(Number(price)).toLocaleString(locale))}\u00a0FCFA`;

  /** Prices stored in FCFA, displayed in the currency chosen by the visitor (euros rounded to the unit from 10 €). */
  const formatPrice = (price: number | string): string => {
    if (deviseCourante === "XOF") return formatFcfa(price);
    const euros = Number(price) / FCFA_PAR_EURO;
    const decimales = euros < 10 ? 2 : 0;
    return espaces(euros.toLocaleString(locale, {
      style: "currency", currency: "EUR", minimumFractionDigits: decimales, maximumFractionDigits: decimales,
    }));
  };

  return {
    langue: () => langueFormat,
    /** Picks the text of the language: selon({ fr: "…", en: "…" }). */
    selon: <T>(textes: { fr: T; en: T }): T => textes[langueFormat],
    TYPE_LABELS: libelles(TYPES, langueFormat),
    ROLE_LABELS: libelles(ROLES, langueFormat),
    formatFcfa,
    formatPrice,

    /** Where room is tight (prices on the map): "45 000 F" or "69 €". */
    formatPrixCourt: (price: number | string) => (deviseCourante === "XOF" ? formatFcfa(price).replace(/FCFA$/, "F") : formatPrice(price)),

    formatDate(d: string, opts: Intl.DateTimeFormatOptions = { day: "numeric", month: "short", year: "numeric" }) {
      if (!d) return "-";
      return new Date(d).toLocaleDateString(locale, opts);
    },

    /** "samedi 2 novembre à 14 h 30" / "Saturday 2 November at 14:30" from the ticket time
     * (YYYY-MM-DDTHH:MM, local time of the airport). */
    dateVol(arriveeLocale: string) {
      const [jour, heure] = arriveeLocale.split("T");
      const date = new Date(`${jour}T12:00:00`).toLocaleDateString(locale, { weekday: "long", day: "numeric", month: "long" });
      return langueFormat === "en" ? `${date} at ${heure}` : `${date} à ${heure.replace(":", " h ")}`;
    },

    moisAnnee(iso: string) {
      return new Date(`${iso}T00:00:00`).toLocaleDateString(locale, { month: "long", year: "numeric" });
    },
  };
}

const FORMATS = { fr: creerFormats("fr"), en: creerFormats("en") };

/** Format functions of a language: see useFormat (lib/format.ts). */
export function formats(locale: string) {
  return FORMATS[locale === "en" ? "en" : "fr"];
}

export const TYPE_LABELS = FORMATS.fr.TYPE_LABELS;
export const ROLE_LABELS = FORMATS.fr.ROLE_LABELS;
export const formatFcfa = (price: number | string) => FORMATS[langueCourante].formatFcfa(price);
export const formatPrice = (price: number | string) => FORMATS[langueCourante].formatPrice(price);
export const formatDate = (d: string, opts?: Intl.DateTimeFormatOptions) => FORMATS[langueCourante].formatDate(d, opts);

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
