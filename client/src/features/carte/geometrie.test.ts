import { describe, expect, it } from "vitest";
import { CENTRE_LOME, arrondi, centreDeVille, regrouper, zoneCirculaire } from "./geometrie";

describe("centreDeVille", () => {
  it("finds a city without accents or capitals", () => {
    expect(centreDeVille(" LOME ")).toEqual(CENTRE_LOME);
    expect(centreDeVille("Kpalimé")).toEqual(centreDeVille("kpalime"));
  });

  it("answers null for an unknown place", () => {
    expect(centreDeVille("Bè Kpota")).toBeNull();
    expect(centreDeVille("")).toBeNull();
  });
});

describe("arrondi", () => {
  it("keeps the 6 decimals the API accepts", () => {
    expect(arrondi({ lat: 6.13751234567, lng: -1.21234567891 })).toEqual({ lat: 6.137512, lng: -1.212346 });
  });
});

describe("regrouper", () => {
  const taille = { largeur: 84, hauteur: 34 };

  it("gathers the prices that would overlap", () => {
    const a = { x: 100, y: 100 }, b = { x: 150, y: 110 }, c = { x: 400, y: 100 };

    expect(regrouper([a, b, c], taille)).toEqual([[a, b], [c]]);
  });

  it("keeps apart two prices that only share a column", () => {
    const a = { x: 100, y: 100 }, b = { x: 100, y: 140 };

    expect(regrouper([a, b], taille)).toEqual([[a], [b]]);
  });
});

describe("zoneCirculaire", () => {
  const zone = zoneCirculaire({ lat: 6.1375, lng: 1.2123 }, 400);
  const contour = zone.geometry.coordinates[0];

  it("closes the polygon", () => {
    expect(contour.at(-1)?.[0]).toBeCloseTo(contour[0][0], 8);
    expect(contour.at(-1)?.[1]).toBeCloseTo(contour[0][1], 8);
  });

  it("stays at the requested distance from the centre", () => {
    for (const [lng, lat] of contour) {
      const nord = (lat - 6.1375) * 111_320;
      const est = (lng - 1.2123) * 111_320 * Math.cos((6.1375 * Math.PI) / 180);
      expect(Math.hypot(nord, est)).toBeCloseTo(400, 3);
    }
  });
});
