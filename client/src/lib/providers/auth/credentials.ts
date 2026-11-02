import Credentials from "next-auth/providers/credentials";
import { ouvrirSession } from "@/lib/api/auth/connexion";

export const credentialsProvider = Credentials({
  id: "credentials",
  name: "Credentials",
  credentials: {
    email: { label: "Email", type: "email" },
    password: { label: "Password", type: "password" },
    captcha: { label: "Captcha", type: "text" },
  },
  async authorize(credentials, request) {
    if (!credentials?.email || !credentials?.password) return null;
    return ouvrirSession("/v1/auth/login/", {
      email: String(credentials.email),
      password: String(credentials.password),
      captcha: String(credentials.captcha ?? ""),
    }, request);
  },
});
