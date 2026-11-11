import type { MetadataRoute } from "next";
import { routing } from "@/i18n/routing";
import { CHEMINS_PRIVES, SITE_URL } from "@/lib/seo";

// Computed on demand: the address of the sitemap is the one of the environment serving it, not the one of the build
export const dynamic = "force-dynamic";

const NON_TRADUITS: readonly string[] = ["/backoffice", "/agent", "/api/"];

/** robots.txt: public pages crawled, private pages (account, messages, payment, back-office) excluded. */
export default function robots(): MetadataRoute.Robots {
  const autresLangues = routing.locales.filter((l) => l !== routing.defaultLocale);
  // Site pages exist per language (/en/…); the API, the back-office and the agent space exist only once
  const prives = CHEMINS_PRIVES.flatMap((c) =>
    NON_TRADUITS.includes(c) ? [c] : [c, ...autresLangues.map((l) => `/${l}${c}`)]);
  return {
    rules: [{
      userAgent: "*",
      allow: ["/", "/profil/aide", ...autresLangues.map((l) => `/${l}/profil/aide`)],
      disallow: prives,
    }],
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
