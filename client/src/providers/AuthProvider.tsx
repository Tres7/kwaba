"use client";

import { useEffect } from "react";
import { SessionProvider, signOut, useSession } from "next-auth/react";

// Signs out if the Django refresh token has expired
function SessionExpiree() {
  const { data: session } = useSession();

  useEffect(() => {
    if (session?.error === "RefreshAccessTokenError") signOut({ callbackUrl: "/login?expired=1" });
  }, [session]);

  return null;
}

export default function AuthProvider({ children }: { children: React.ReactNode }) {
  return (
    // Reads the session every minute while a tab is open: each read extends the session by 5 min
    // (session.maxAge in auth.ts) and renews the access token before it expires
    <SessionProvider refetchInterval={60} refetchOnWindowFocus>
      <SessionExpiree />
      {children}
    </SessionProvider>
  );
}
