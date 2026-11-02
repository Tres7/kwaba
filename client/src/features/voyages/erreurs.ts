import { apiErrorMessage } from "@/lib/api";

export function messageErreur(err: unknown, defaut: string) {
  const data = (err as { response?: { data?: Record<string, string[] | string> } }).response?.data;
  if (data && typeof data === "object" && !("detail" in data)) {
    const premier = Object.values(data)[0];
    return Array.isArray(premier) ? premier[0] : String(premier);
  }
  return apiErrorMessage(err, defaut);
}
