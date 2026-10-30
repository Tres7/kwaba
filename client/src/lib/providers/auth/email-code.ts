import Credentials from "next-auth/providers/credentials";
import { ouvrirSession } from "@/lib/api/auth/connexion";

/** Email verification: the 6-digit code proves ownership of the address and opens the session directly. */
export const emailCodeProvider = Credentials({
  id: "email-code",
  name: "Email code",
  credentials: {
    email: { label: "Email", type: "email" },
    code: { label: "Code", type: "text" },
  },
  async authorize(credentials, request) {
    if (!credentials?.email || !credentials?.code) return null;
    return ouvrirSession("/v1/auth/verify/", { email: String(credentials.email), code: String(credentials.code) }, request);
  },
});
