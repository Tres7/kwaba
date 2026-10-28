import type { Metadata } from "next";
import { hasLocale } from "next-intl";
import { getTranslations } from "next-intl/server";
import { routing, type Langue } from "@/i18n/routing";

/** Public address of the site, without a trailing "/": absolute URLs of the sitemap, link previews and canonicals. */
export const SITE_URL = (process.env.NEXT_PUBLIC_SITE_URL || process.env.AUTH_URL || "http://localhost:3000").replace(/\/+$/, "");

export const IMAGE_PARTAGE = "/brand/kwaba-partage-1200x630.png";

/** Indexable public pages (without language prefix). Listing and organisation pages are added to them. */
export const PAGES_PUBLIQUES = [
  "/", "/recherche", "/decouvrir", "/transfert", "/location", "/together", "/concierge", "/hote",
  "/give", "/give/impact", "/profil/aide",
  "/cgu", "/cgv", "/confidentialite", "/cookies", "/mentions-legales", "/remboursement",
] as const;

/**
 * Private pages or pages of no interest to a search engine (robots.txt): they redirect to sign-in or only
 * show the user's data. /profil/aide (help centre) stays public.
 *
 * The sign-in pages (/login, /register, /verify, /mot-de-passe-oublie) are not listed: they carry "noindex"
 * (app/[locale]/(auth)/layout.tsx), which Google could not read if crawling them were forbidden. Without it, every
 * /login?callbackUrl=… was reported as a duplicate page without a canonical URL.
 */
export const CHEMINS_PRIVES = [
  "/profil", "/favoris", "/messages", "/reservation", "/hote/espace", "/give/don", "/together/", "/transfert/", "/location/",
  "/backoffice", "/agent", "/alertes", "/api/",
] as const;

export function langueDe(valeur: string): Langue {
  return hasLocale(routing.locales, valeur) ? valeur : routing.defaultLocale;
}

/** Public path of a page in a language: /recherche (French) or /en/recherche (English). */
export function cheminLocalise(locale: Langue, chemin: string): string {
  if (locale === routing.defaultLocale) return chemin;
  return chemin === "/" ? `/${locale}` : `/${locale}${chemin}`;
}

/** The two language versions of a page, and the French version by default (hreflang x-default). */
export function versionsLinguistiques(chemin: string): Record<string, string> {
  return {
    fr: cheminLocalise("fr", chemin),
    en: cheminLocalise("en", chemin),
    "x-default": cheminLocalise(routing.defaultLocale, chemin),
  };
}

interface PageSeo {
  locale: Langue;
  /** Path without language prefix, e.g. /hebergements/<id> */
  chemin: string;
  titre: string;
  description?: string;
  image?: string | null;
  /** Title displayed as is, without "· Kwa-Ba" (home page). */
  titreComplet?: boolean;
  indexable?: boolean;
}

/**
 * Metadata of a public page: title, description, canonical URL, FR / EN versions and link preview.
 * Every indexable page must provide them: without them, Google knows neither which URL to keep nor which is
 * the version in the other language (Next.js replaces the parent's openGraph block instead of merging it).
 */
export function metadataPage({ locale, chemin, titre, description, image, titreComplet, indexable = true }: PageSeo): Metadata {
  const url = cheminLocalise(locale, chemin);
  const images = image ? [{ url: image }] : [{ url: IMAGE_PARTAGE, width: 1200, height: 630 }];
  return {
    title: titreComplet ? { absolute: titre } : titre,
    description,
    alternates: { canonical: url, languages: versionsLinguistiques(chemin) },
    openGraph: {
      type: "website",
      siteName: "Kwa-Ba",
      locale: locale === "en" ? "en_GB" : "fr_FR",
      alternateLocale: locale === "en" ? "fr_FR" : "en_GB",
      url,
      title: titre,
      description,
      images,
    },
    twitter: { card: "summary_large_image", title: titre, description, images: images.map((i) => i.url) },
    ...(indexable ? {} : { robots: { index: false, follow: true } }),
  };
}

/**
 * Private page under a public page (/transfert/<id>, /together/<id>…): keeps the title of its section but is
 * neither indexed nor attached to the canonical URL of the public page it inherits from.
 */
export const METADATA_PRIVEE: Metadata = {
  alternates: { canonical: null, languages: {} },
  robots: { index: false, follow: false },
};

/** Metadata of a page whose title and description are in messages/*.json (meta.pages.<cle>). */
export async function metadataTraduite(params: Promise<{ locale: string }>, cle: string, chemin: string): Promise<Metadata> {
  const locale = langueDe((await params).locale);
  const t = await getTranslations({ locale, namespace: "meta.pages" });
  return metadataPage({ locale, chemin, titre: t(`${cle}.titre`), description: t(`${cle}.description`) });
}

/** Server-side API read (sitemap, metadata): cached, null if the API does not respond. */
export async function lireApi<T>(chemin: string, revalidate = 600): Promise<T | null> {
  const base = process.env.INTERNAL_API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
  try {
    const res = await fetch(`${base}${chemin}`, { next: { revalidate }, signal: AbortSignal.timeout(5000) });
    return res.ok ? ((await res.json()) as T) : null;
  } catch {
    return null;
  }
}
