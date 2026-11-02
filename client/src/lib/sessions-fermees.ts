// Sessions closed recently, by refresh token, with the end of their retention. Kept in the memory of the Next.js server:
// a single process in production (deploy/vps/compose.yml).
const fermees = new Map<string, number>();

/**
 * Remembers a session that was just signed out of. A session read still in flight at that moment puts the cookie back
 * just after it was deleted: the next read finds the session here and closes it for good. `dureeMs`: lifetime of the
 * cookie, beyond which one that came back has expired anyway.
 */
export function fermerSession(refreshToken: string, dureeMs: number) {
  const maintenant = Date.now();
  for (const [jeton, fin] of fermees) {
    if (fin <= maintenant) fermees.delete(jeton);
  }
  fermees.set(refreshToken, maintenant + dureeMs);
}

export function sessionFermee(refreshToken?: string): boolean {
  return !!refreshToken && (fermees.get(refreshToken) ?? 0) > Date.now();
}
