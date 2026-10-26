import { defineRouting } from "next-intl/routing";

/** Site languages: French without prefix (kwa-ba.com/…), English under /en (kwa-ba.com/en/…). */
export const routing = defineRouting({
  locales: ["fr", "en"],
  defaultLocale: "fr",
  localePrefix: "as-needed",
  // NEXT_LOCALE cookie (chosen language): 1 year, declared in the cookie policy
  localeCookie: { maxAge: 60 * 60 * 24 * 365 },
});

export type Langue = (typeof routing.locales)[number];
