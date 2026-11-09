/** Position measured on site with the agent's phone, at the visit: once the listing is validated, it replaces the point
 * placed by the host (travellers still only see an approximate zone). */
export interface PositionMesuree {
  latitude: number;
  longitude: number;
  /** Accuracy announced by the phone, in metres */
  precision: number;
}

/** Same limit as the server: beyond, the GPS has not fixed yet (indoors) and the point would mislead the travellers. */
export const PRECISION_MAX_M = 150;

/** From this gap, the agent is asked to check that they are at the right place. */
export const ECART_A_VERIFIER_M = 500;

/** Distance in metres between two points (haversine). */
export function distanceMetres(a: { lat: number; lng: number }, b: { lat: number; lng: number }): number {
  const rad = (x: number) => (x * Math.PI) / 180;
  const h = Math.sin(rad(b.lat - a.lat) / 2) ** 2
    + Math.cos(rad(a.lat)) * Math.cos(rad(b.lat)) * Math.sin(rad(b.lng - a.lng) / 2) ** 2;
  return 2 * 6_371_000 * Math.asin(Math.sqrt(h));
}

/** "850 m", "1,1 km". */
export function formatDistance(metres: number): string {
  if (metres < 1000) return `${Math.round(metres)} m`;
  return `${(metres / 1000).toLocaleString("fr-FR", { maximumFractionDigits: 1 })} km`;
}

/** The fields sent with the visit decision. */
export function champsPosition(position: PositionMesuree): Record<string, string> {
  return {
    latitude: position.latitude.toFixed(6),
    longitude: position.longitude.toFixed(6),
    precision: String(Math.round(position.precision)),
  };
}

/** Google Maps on this exact point, to check it before saving it. */
export function lienCarte(point: { lat: number; lng: number }): string {
  return `https://www.google.com/maps/search/?api=1&query=${point.lat.toFixed(6)},${point.lng.toFixed(6)}`;
}
