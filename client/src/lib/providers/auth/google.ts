import Credentials from "next-auth/providers/credentials";
import { ouvrirSession } from "@/lib/api/auth/connexion";

/** Sign-in with the identity token given by Google in the browser, checked by the API. */
export const googleProvider = Credentials({
  id: "google-id-token",
  name: "Google",
  credentials: {
    idToken: { label: "Google ID token", type: "text" },
  },
  async authorize(credentials, request) {
    if (!credentials?.idToken) return null;
    return ouvrirSession("/v1/auth/google/", { id_token: String(credentials.idToken) }, request);
  },
});
