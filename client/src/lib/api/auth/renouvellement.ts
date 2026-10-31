// Renewals in flight or just finished, by refresh token. Kept in the memory of the Next.js server: a single process in
// production (deploy/vps/compose.yml).
const FENETRE_MS = 30_000;
const recents = new Map<string, { resultat: Promise<unknown>; fin: number }>();

/**
 * Two tabs can renew the session at the same time, with the same refresh token. The API rotates it and refuses the old one:
 * the second call would sign the visitor out. So a refresh token is sent once, and the other calls share its answer.
 * `reussi`: a renewal that did not go through (API unreachable) is not shared, the next call tries again.
 */
export function renouvelerUneFois<T>(refreshToken: string, renouveler: () => Promise<T>, reussi: (resultat: T) => boolean): Promise<T> {
  const maintenant = Date.now();
  for (const [jeton, { fin }] of recents) {
    if (fin <= maintenant) recents.delete(jeton);
  }
  const existant = recents.get(refreshToken);
  if (existant) return existant.resultat as Promise<T>;
  const resultat = renouveler().then(
    (valeur) => {
      if (!reussi(valeur)) recents.delete(refreshToken);
      return valeur;
    },
    (erreur) => {
      recents.delete(refreshToken);
      throw erreur;
    },
  );
  recents.set(refreshToken, { resultat, fin: maintenant + FENETRE_MS });
  return resultat;
}
