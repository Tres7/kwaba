/**
 * Public addresses, read when the Next.js server starts (AUTH_URL of client.env), never at build time: one image serves
 * the preprod and the production.
 */
export const SITE_URL = (process.env.AUTH_URL || "http://localhost:3000").replace(/\/+$/, "");

/** Public address of the API: under the site (/api), except in development where Django has its own port. */
export const API_PUBLIQUE = (process.env.NEXT_PUBLIC_API_URL || `${SITE_URL}/api`).replace(/\/+$/, "");
