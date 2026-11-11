/** Public values of the environment, sent to the browser by Document.tsx (PublicConfigProvider). */
export interface ConfigPublique {
  /** Kwa-Ba contact address (business mailbox), shown on the site */
  contactEmail: string;
  /** OAuth client of the Google sign-in; empty: the Google button is hidden */
  googleClientId: string;
}

export const CONTACT_EMAIL_DEFAUT = "info@kwa-ba.com";

/**
 * Read on the server at each request (client.env of the environment), never baked into the image at build time.
 * The NEXT_PUBLIC_* names remain accepted for an older local .env.
 */
export function lireConfigPublique(): ConfigPublique {
  return {
    contactEmail: process.env.CONTACT_EMAIL || process.env.NEXT_PUBLIC_CONTACT_EMAIL || CONTACT_EMAIL_DEFAUT,
    googleClientId: process.env.GOOGLE_CLIENT_ID || process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || "",
  };
}
