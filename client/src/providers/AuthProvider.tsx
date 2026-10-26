"use client";

import { useEffect } from "react";
import { SessionProvider, signOut, useSession } from "next-auth/react";
import { setApiAccessToken } from "@/lib/api";

// Copies the session token into the API client (sign-in, sign-out, account change)
// and signs out if the Django refresh token has expired
function SessionTokenSync() {
  const { data: session, status } = useSession();

  useEffect(() => {
    if (status === "loading") return;
    if (session?.error === "RefreshAccessTokenError") {
      setApiAccessToken(null);
      signOut({ callbackUrl: "/login?expired=1" });
      return;
    }
    setApiAccessToken(session?.accessToken || null);
  }, [session, status]);

  return null;
}

export default function AuthProvider({ children }: { children: React.ReactNode }) {
  return (
    // Reads the session every minute while a tab is open: each read extends the session by 5 min
    // (session.maxAge in auth.ts) and renews the access token before it expires
    <SessionProvider refetchInterval={60} refetchOnWindowFocus>
      <SessionTokenSync />
      {children}
    </SessionProvider>
  );
}
