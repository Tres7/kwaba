import { CredentialsSignin } from "next-auth";
import { getApiBaseUrl } from "@/lib/api-url";
import type { BackendAuthResponse } from "@/types/api/auth";

/** Refused sign-in: only `code` reaches the browser, the sign-in forms turn it into a message. */
function refus(code: string) {
  const erreur = new CredentialsSignin();
  erreur.code = code;
  return erreur;
}

/**
 * Sign-in call made by this server: the API's tokens go straight into the encrypted session cookie, the browser never
 * sees them. `request`: the request received by Auth.js, for the visitor's address (X-Forwarded-For chain from nginx).
 * Without it, the API would see the address of this container for every visitor (audit log, limits per address).
 */
export async function ouvrirSession(chemin: string, corps: Record<string, unknown>, request: Request) {
  const adressesClient = request.headers.get("x-forwarded-for");
  let res: Response;
  try {
    res = await fetch(`${getApiBaseUrl()}${chemin}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(adressesClient ? { "X-Forwarded-For": adressesClient } : {}),
      },
      body: JSON.stringify(corps),
      cache: "no-store",
    });
  } catch {
    throw refus("serveur");
  }

  const data = (await res.json().catch(() => ({}))) as Partial<BackendAuthResponse> & { code?: string };
  // 429: limit per address (DRF, without a code) or per email
  if (!res.ok) throw refus(res.status === 429 ? "too_many_attempts" : (data.code ?? "refus"));
  if (!data.access || !data.refresh || !data.user) throw refus("serveur");

  return {
    id: data.user.id,
    name: `${data.user.first_name} ${data.user.last_name}`.trim(),
    email: data.user.email,
    image: data.user.avatar_url ?? null,
    accessToken: data.access,
    refreshToken: data.refresh,
    role: data.user.role,
  };
}
