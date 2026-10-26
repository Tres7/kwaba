import NextAuth from "next-auth";
import type { JWT } from "next-auth/jwt";
import { getApiBaseUrl } from "@/lib/api-url";
import { fetchBackendUser } from "@/lib/api/auth/me";
import { credentialsProvider } from "@/lib/providers/auth/credentials";
import { backendSessionProvider } from "@/lib/providers/auth/backend-session";

// Renews the access token 30 s before it expires
const REFRESH_MARGIN_MS = 30_000;

function decodeExpiry(accessToken?: string): number {
  if (!accessToken) return 0;
  try {
    const payload = accessToken.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    const { exp } = JSON.parse(atob(payload)) as { exp?: number };
    return exp ? exp * 1000 : 0;
  } catch {
    return 0;
  }
}

async function refreshAccessToken(token: JWT): Promise<JWT> {
  let res: Response;
  try {
    res = await fetch(`${getApiBaseUrl()}/v1/auth/refresh/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh: token.refreshToken }),
    });
  } catch {
    // API unreachable (restart, network): the session is kept, the renewal will be tried again
    return token;
  }
  // Only an explicit refusal from the API (expired, revoked or invalid token) closes the session;
  // a transient error (5xx, 429) must not sign the user out
  if (res.status === 400 || res.status === 401) return { ...token, error: "RefreshAccessTokenError" };
  if (!res.ok) return token;
  try {
    const data = (await res.json()) as { access: string; refresh?: string };
    return {
      ...token,
      accessToken: data.access,
      refreshToken: data.refresh ?? token.refreshToken,
      accessTokenExpires: decodeExpiry(data.access),
      error: undefined,
    };
  } catch {
    return token;
  }
}

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [credentialsProvider, backendSessionProvider],
  trustHost: true,

  callbacks: {
    async jwt({ token, user, trigger, session }) {
      if (user) {
        token.accessToken = user.accessToken;
        token.refreshToken = user.refreshToken;
        token.accessTokenExpires = decodeExpiry(user.accessToken);
        token.role = user.role;
        token.userId = user.id ?? undefined;
        token.error = undefined;
      }

      if (token.refreshToken && Date.now() >= (token.accessTokenExpires ?? 0) - REFRESH_MARGIN_MS) {
        token = await refreshAccessToken(token);
      }

      // useSession().update() (new name, becoming a host): the profile is read again from the API instead of trusting
      // the values sent by the browser, which could otherwise give itself the "admin" role
      if (trigger === "update" && session && token.accessToken && !token.error) {
        const me = await fetchBackendUser(token.accessToken);
        if (me) {
          token.name = `${me.first_name} ${me.last_name}`.trim();
          token.role = me.role;
          token.picture = me.avatar_url;
        }
      }
      return token;
    },
    async session({ session, token }) {
      session.accessToken = token.accessToken ?? "";
      session.user.id = token.userId ?? "";
      session.user.role = token.role ?? "voyageur";
      session.error = token.error;
      return session;
    },
  },

  pages: {
    signIn: "/login",
    newUser: "/register",
  },
  session: {
    strategy: "jwt",
    // 5 min after leaving the site (tab or browser closed), signing in again is needed: while a tab
    // is open, AuthProvider reads the session every minute and each read pushes the expiry back
    maxAge: 5 * 60,
  },
  cookies: {
    sessionToken: {
      options: {
        httpOnly: true,
        sameSite: "lax",
        path: "/",
        secure: process.env.NODE_ENV === "production",
      },
    },
  },
});
