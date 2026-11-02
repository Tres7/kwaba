export interface PointCarte {
  lat: number;
  lng: number;
}

export const CENTRE_LOME: PointCarte = { lat: 6.1375, lng: 1.2123 };

const METRES_PAR_DEGRE = 111_320;
const COTES_ZONE = 64;

// Starting view of the map when no listing gives it: destinations where Kwa-Ba has or expects listings
const VILLES: Record<string, PointCarte> = {
  lome: CENTRE_LOME,
  kpalime: { lat: 6.9, lng: 0.6333 },
  atakpame: { lat: 7.5333, lng: 1.1333 },
  sokode: { lat: 8.9833, lng: 1.1333 },
  kara: { lat: 9.5511, lng: 1.1861 },
  dapaong: { lat: 10.8667, lng: 0.2 },
  aneho: { lat: 6.2333, lng: 1.6 },
  cotonou: { lat: 6.3654, lng: 2.4183 },
  ouagadougou: { lat: 12.3714, lng: -1.5197 },
  abidjan: { lat: 5.3364, lng: -4.0267 },
  accra: { lat: 5.6037, lng: -0.187 },
};

const normaliser = (texte: string) => texte.normalize("NFD").replace(/[̀-ͯ]/g, "").trim().toLowerCase();

export function centreDeVille(ville: string): PointCarte | null {
  return VILLES[normaliser(ville)] ?? null;
}

/** About 10 cm: the precision the API stores. */
export function arrondi({ lat, lng }: PointCarte): PointCarte {
  return { lat: Number(lat.toFixed(6)), lng: Number(lng.toFixed(6)) };
}

/** Points that would overlap on screen, gathered: each group starts from its first point. */
export function regrouper<T extends { x: number; y: number }>(points: T[], { largeur, hauteur }: { largeur: number; hauteur: number }): T[][] {
  const groupes: T[][] = [];
  for (const point of points) {
    const groupe = groupes.find(([{ x, y }]) => Math.abs(x - point.x) < largeur && Math.abs(y - point.y) < hauteur);
    if (groupe) groupe.push(point);
    else groupes.push([point]);
  }
  return groupes;
}

/** Circle on the ground, as a polygon: the zone of a listing whose exact position is not shown. */
export function zoneCirculaire({ lat, lng }: PointCarte, rayonM: number) {
  const degresNord = rayonM / METRES_PAR_DEGRE;
  const degresEst = degresNord / Math.cos((lat * Math.PI) / 180);
  const contour = Array.from({ length: COTES_ZONE + 1 }, (_, i) => {
    const angle = (i / COTES_ZONE) * 2 * Math.PI;
    return [lng + degresEst * Math.cos(angle), lat + degresNord * Math.sin(angle)];
  });
  return { type: "Feature" as const, properties: {}, geometry: { type: "Polygon" as const, coordinates: [contour] } };
}
