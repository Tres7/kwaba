import Credentials from "next-auth/providers/credentials";
import { fetchBackendUser } from "@/lib/api/auth/me";

/**
 * Opens the session with tokens already obtained from the API (email verification, Google sign-in).
 * Only the tokens are taken from the browser: id, email, name and role are read again from the API with the
 * access token, otherwise anyone could forge an "admin" session.
 */
export const backendSessionProvider = Credentials({
  id: "backend-session",
  name: "Backend Session",
  credentials: {
    accessToken: { label: "Access Token", type: "text" },
    refreshToken: { label: "Refresh Token", type: "text" },
  },
  async authorize(credentials) {
    if (!credentials?.accessToken || !credentials?.refreshToken) return null;

    const accessToken = String(credentials.accessToken);
    const user = await fetchBackendUser(accessToken);
    if (!user) return null;

    return {
      id: user.id,
      name: `${user.first_name} ${user.last_name}`.trim(),
      email: user.email,
      image: user.avatar_url,
      accessToken,
      refreshToken: String(credentials.refreshToken),
      role: user.role,
    };
  },
});
