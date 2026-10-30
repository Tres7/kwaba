import { getApiBaseUrl } from "@/lib/api-url";
import { LoginResponse } from "@/types/api/auth";

export async function authenticateWithCredentials(
  email: string,
  password: string,
  captcha = "",
  adressesClient?: string | null
): Promise<LoginResponse> {
  const res = await fetch(`${getApiBaseUrl()}/v1/auth/login/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      // Call made by this server: without the chain received from nginx, the API would see the address of this
      // container for every visitor (audit log, limit per address)
      ...(adressesClient ? { "X-Forwarded-For": adressesClient } : {}),
    },
    body: JSON.stringify({ email, password, captcha }),
  });

  const data = await res.json();

  if (!res.ok) {
    const error = new Error(data.detail ?? "Identifiants invalides.") as Error & {
      code?: string;
    };
    // Limit per address (DRF, without a code) or per email
    error.code = res.status === 429 ? "too_many_attempts" : data.code;
    throw error;
  }

  return data;
}