import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";
import { getSession, signOut } from "next-auth/react";
import { getApiBaseUrl } from "@/lib/api-url";
import { langue, selon } from "@/lib/utils";


const api = axios.create({
  baseURL:  getApiBaseUrl(),
  headers: {
    "Content-Type": "application/json",
  },
});

// Token kept up to date by SessionTokenSync (providers/AuthProvider.tsx) at every session change.
// undefined = session not known yet: it is then asked once from NextAuth.
let accessToken: string | null | undefined;

export function setApiAccessToken(token: string | null) {
  accessToken = token;
}

/** Current access token, for requests made outside axios (Concierge SSE stream). */
export async function jetonAcces(): Promise<string | null> {
  if (accessToken !== undefined) return accessToken;
  return (await getSession())?.accessToken ?? null;
}

api.interceptors.request.use(async (config) => {
  // User's language: Concierge answers and, eventually, API messages
  config.headers["Accept-Language"] = langue();
  if (typeof window !== "undefined") {
    // Avoids a call to /api/auth/session per request (the messaging polling would make one every 4 s)
    const token = accessToken !== undefined ? accessToken : (await getSession())?.accessToken;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// Several requests may fail at the same time: a single shared renewal
let refreshing: Promise<{ token: string | null; expiree: boolean }> | null = null;

/** `expiree`: the API refused the refresh token (session really over). An unreadable session
 * (network down when the computer wakes up, for example) is not an expiry: the user is not signed out. */
async function refreshAccessToken(): Promise<{ token: string | null; expiree: boolean }> {
  if (!refreshing) {
    // getSession() calls NextAuth again, whose jwt callback renews the expired Django token
    refreshing = getSession()
      .then((session) => {
        const expiree = session?.error === "RefreshAccessTokenError";
        const token = session && !expiree ? session.accessToken || null : null;
        if (session) setApiAccessToken(token);
        return { token, expiree };
      })
      .finally(() => { refreshing = null; });
  }
  return refreshing;
}

api.interceptors.response.use(
  (res) => res,
  async (error: AxiosError) => {
    const config = error.config as (InternalAxiosRequestConfig & { _retried?: boolean }) | undefined;

    if (typeof window !== "undefined" && error.response?.status === 401 && config?.headers?.Authorization) {
      // Cached token expired: it is renewed, then the request is replayed once
      if (config._retried) return Promise.reject(error);
      config._retried = true;
      const { token, expiree } = await refreshAccessToken();
      if (token && `Bearer ${token}` !== config.headers.Authorization) {
        config.headers.Authorization = `Bearer ${token}`;
        return api(config);
      }
      // Renewal impossible for now (API or network unavailable): the session is kept
      if (!expiree) return Promise.reject(error);
      // Django refresh token refused: clean sign-out
      setApiAccessToken(null);
      // The sign-in page stays in the current language; the return goes without the /en prefix (added by the router)
      const prefixe = langue() === "en" ? "/en" : "";
      const chemin = window.location.pathname.replace(/^\/en(?=\/|$)/, "") || "/";
      const callbackUrl = `${prefixe}/login?expired=1&callbackUrl=${encodeURIComponent(chemin)}`;
      await signOut({ callbackUrl });
    }
    return Promise.reject(error);
  }
);

/** Extracts a readable message from a DRF error ({detail}, {field: [msg]}, ...). */
export function apiErrorMessage(err: unknown, fallback?: string): string {
  const e = err as AxiosError<Record<string, unknown>>;
  if (!e?.response) return selon({ fr: "Impossible de contacter le serveur.", en: "Unable to reach the server." });
  // Pre-launch mode (config/prelancement.py on the API): bookings and payments are not open yet
  if (e.response.data?.code === "prelancement") {
    return selon({
      fr: "Kwa-Ba ouvre bientôt : les réservations et les paiements ne sont pas encore ouverts.",
      en: "Kwa-Ba opens soon: bookings and payments are not open yet.",
    });
  }
  if (e.response.data?.code === "preinscription_requise") {
    return selon({
      fr: "Acceptez d'abord la pré-inscription pour créer votre annonce.",
      en: "Please accept the pre-registration first to create your listing.",
    });
  }
  return firstErrorMessage(e.response.data) ?? fallback ?? selon({ fr: "Une erreur est survenue. Veuillez réessayer.", en: "Something went wrong. Please try again." });
}

export function firstErrorMessage(data: unknown): string | undefined {
  if (!data) return undefined;
  if (typeof data === "string") return data.length < 300 ? data : undefined;
  if (Array.isArray(data)) return firstErrorMessage(data[0]);
  if (typeof data === "object") {
    const obj = data as Record<string, unknown>;
    if (typeof obj.detail === "string") return obj.detail;
    for (const value of Object.values(obj)) {
      const msg = firstErrorMessage(value);
      if (msg) return msg;
    }
  }
  return undefined;
}

export default api;
