import { useLocale } from "next-intl";
import { formats } from "@/lib/utils";

/**
 * Dates, prices and labels in the language of the page. Same names as the functions of lib/utils.ts, which only follow the
 * language in the browser: on the server, several requests in different languages are rendered at the same time.
 */
export function useFormat() {
  return formats(useLocale());
}
