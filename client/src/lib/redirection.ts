// Never contacted: only used to resolve an address the way a browser does
const BASE = "http://kwaba.invalid";

/**
 * Internal address to open after signing in, "/" for anything else (prevents open redirects). The check is made on the
 * address as the browser reads it: a backslash counts as a slash and tabs and line breaks are dropped, so /\evil.com
 * and /<tab>/evil.com lead to another site. The result is checked too: /.//evil.com stays on the site once resolved,
 * but its path, //evil.com, would not.
 */
export function safeCallback(url: string | null): string {
  if (!url) return "/";
  try {
    const cible = new URL(url, BASE);
    const chemin = cible.pathname + cible.search + cible.hash;
    return cible.origin === BASE && !chemin.startsWith("//") ? chemin : "/";
  } catch {
    return "/";
  }
}
