import type { Langue } from "@/i18n/routing";
import type { Hebergement } from "@/types/api/models";
import { villeDuNom } from "./destinations";
import { cheminLocalise, SITE_URL } from "./seo";
import { prixNuitFraisInclus, SERVICE_FEE_RATE } from "./utils";

/**
 * Structured data (schema.org, JSON-LD) read by search engines: the listing with its price, the breadcrumb, the
 * list of a destination page, and Kwa-Ba itself on the home page. Rendered by components/seo/JsonLd.tsx.
 */
type Objet = Record<string, unknown>;

const CONTEXTE = "https://schema.org";

const absolue = (url: string) => new URL(url, SITE_URL).href;
const urlPage = (locale: Langue, chemin: string) => `${SITE_URL}${cheminLocalise(locale, chemin)}`;

/** Hotels and hostels have their own schema.org type; the other listings are lodging businesses. */
const TYPES_SCHEMA: Record<string, string> = { chambre_hotel: "Hotel", auberge: "Hostel" };

/** Price of a night as the listing page shows it first: traveller's service fee included. */
export function prixNuitAffiche(h: Pick<Hebergement, "price_per_night" | "frais_voyageur">): number {
  return prixNuitFraisInclus(Number(h.price_per_night), h.frais_voyageur ?? SERVICE_FEE_RATE).total;
}

/**
 * A listing (LodgingBusiness and its Offer). Never the exact position nor the landmark: travellers only get them
 * once their booking is paid.
 */
export function donneesLogement(h: Hebergement, locale: Langue, description: string): Objet {
  const url = urlPage(locale, `/hebergements/${h.id}`);
  const ville = villeDuNom(h.city);
  const prix = prixNuitAffiche(h);
  const images = [...new Set([h.image_url, ...(h.images ?? [])].filter(Boolean).map(absolue))];
  return {
    "@context": CONTEXTE,
    "@type": TYPES_SCHEMA[h.type] ?? "LodgingBusiness",
    "@id": url,
    url,
    name: h.name,
    description,
    ...(images.length ? { image: images } : {}),
    address: {
      "@type": "PostalAddress",
      addressLocality: ville?.nom ?? h.city,
      ...(ville ? { addressCountry: ville.pays.toUpperCase() } : {}),
    },
    ...(h.chambres ? { numberOfRooms: h.chambres } : {}),
    ...(h.arrivee_a_partir ? { checkinTime: h.arrivee_a_partir } : {}),
    ...(h.depart_avant ? { checkoutTime: h.depart_avant } : {}),
    ...(h.review_count > 0
      ? { aggregateRating: { "@type": "AggregateRating", ratingValue: h.rating, reviewCount: h.review_count, bestRating: 5, worstRating: 1 } }
      : {}),
    makesOffer: {
      "@type": "Offer",
      url,
      price: prix,
      priceCurrency: "XOF",
      availability: "https://schema.org/InStock",
      priceSpecification: {
        "@type": "UnitPriceSpecification",
        price: prix,
        priceCurrency: "XOF",
        unitCode: "DAY",
        unitText: locale === "en" ? "night" : "nuit",
      },
    },
  };
}

/** Breadcrumb from the home page to the current page (each step: its name and its path without language). */
export function filAriane(locale: Langue, etapes: { nom: string; chemin: string }[]): Objet {
  return {
    "@context": CONTEXTE,
    "@type": "BreadcrumbList",
    itemListElement: etapes.map((e, i) => ({ "@type": "ListItem", position: i + 1, name: e.nom, item: urlPage(locale, e.chemin) })),
  };
}

/** Listings shown by a destination page, in their order on the page. */
export function listeLogements(locale: Langue, logements: Pick<Hebergement, "id">[]): Objet {
  return {
    "@context": CONTEXTE,
    "@type": "ItemList",
    itemListElement: logements.map((h, i) => ({ "@type": "ListItem", position: i + 1, url: urlPage(locale, `/hebergements/${h.id}`) })),
  };
}

/** Kwa-Ba and its site (home page): name, logo and slogan in search results. */
export function donneesSite(locale: Langue, slogan: string): Objet[] {
  const organisation = `${SITE_URL}/#organisation`;
  return [
    { "@context": CONTEXTE, "@type": "Organization", "@id": organisation, name: "Kwa-Ba", url: `${SITE_URL}/`, logo: absolue("/brand/kwaba-icone-512.png"), slogan },
    { "@context": CONTEXTE, "@type": "WebSite", "@id": `${SITE_URL}/#site`, name: "Kwa-Ba", url: `${SITE_URL}/`, inLanguage: locale, publisher: { "@id": organisation } },
  ];
}
