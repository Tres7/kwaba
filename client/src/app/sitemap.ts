import type { MetadataRoute } from "next";
import { cheminLocalise, lireApi, PAGES_PUBLIQUES, SITE_URL, versionsLinguistiques } from "@/lib/seo";
import type { Hebergement } from "@/types/api/models";
import type { Organisation } from "@/types/api/give";
import { filtrerLiens, type ReglagesSite } from "@/lib/modules";

// Computed on demand (never at build time, when the API cannot be reached); API reads are cached
// for an hour (lireApi)
export const dynamic = "force-dynamic";

const PRIORITES: Record<string, number> = { "/": 1, "/recherche": 0.9 };

type Entree = MetadataRoute.Sitemap[number];

/** One URL per language, each announcing its two versions (hreflang): Google links /x and /en/x. */
function entrees(chemin: string, extra: Partial<Entree> = {}): MetadataRoute.Sitemap {
  const absolues = Object.fromEntries(
    Object.entries(versionsLinguistiques(chemin)).filter(([langue]) => langue !== "x-default")
      .map(([langue, url]) => [langue, `${SITE_URL}${url}`]),
  );
  return (["fr", "en"] as const).map((locale) => ({
    url: `${SITE_URL}${cheminLocalise(locale, chemin)}`,
    alternates: { languages: absolues },
    ...extra,
  }));
}

/**
 * sitemap.xml: public pages, available listings and Give organisations, in French and English. Pages of hidden
 * modules are left out (settings read again every 5 minutes; API unreachable: modules hidden).
 */
export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const [logements, reglages] = await Promise.all([
    lireApi<{ results: Hebergement[] }>("/v1/hebergements/", 3600),
    lireApi<ReglagesSite>("/v1/site/", 300),
  ]);
  const organisations = reglages?.modules.give ? await lireApi<{ results: Organisation[] }>("/v1/give/organisations/", 3600) : null;
  const pages = filtrerLiens(PAGES_PUBLIQUES.map((href) => ({ href })), reglages?.modules).map((p) => p.href);

  return [
    ...pages.flatMap((chemin) => entrees(chemin, { priority: PRIORITES[chemin] ?? 0.5 })),
    ...(logements?.results ?? []).flatMap((h) =>
      entrees(`/hebergements/${h.id}`, { priority: 0.8, changeFrequency: "weekly" })),
    ...(organisations?.results ?? []).flatMap((o) => entrees(`/give/${o.slug}`, { priority: 0.6 })),
  ];
}
