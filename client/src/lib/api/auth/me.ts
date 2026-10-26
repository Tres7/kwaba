import { getApiBaseUrl } from "@/lib/api-url";

export type BackendUser = {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
  avatar_url: string | null;
};

/**
 * Profile read by the API with this access token. Source of truth for the identity and role in the session: nothing
 * the browser sends (id, role) gets in without being confirmed by the API. null if the token is refused.
 */
export async function fetchBackendUser(accessToken: string): Promise<BackendUser | null> {
  try {
    const res = await fetch(`${getApiBaseUrl()}/v1/users/me/`, {
      headers: { Authorization: `Bearer ${accessToken}` },
      cache: "no-store",
    });
    if (!res.ok) return null;
    return (await res.json()) as BackendUser;
  } catch {
    return null;
  }
}
