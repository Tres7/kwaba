import { describe, expect, it } from "vitest";
import { champsPosition, distanceMetres, formatDistance } from "./position";

describe("position relevée sur place", () => {
  it("mesure l'écart avec le point de l'hôte", () => {
    expect(distanceMetres({ lat: 6.13, lng: 1.22 }, { lat: 6.14, lng: 1.22 })).toBeCloseTo(1112, -1);
    expect(distanceMetres({ lat: 6.13, lng: 1.22 }, { lat: 6.13, lng: 1.22 })).toBe(0);
  });

  it("affiche la distance en mètres puis en kilomètres", () => {
    expect(formatDistance(849.6)).toBe("850 m");
    expect(formatDistance(1112)).toBe("1,1 km");
  });

  it("envoie six décimales et une précision entière", () => {
    expect(champsPosition({ latitude: 6.1312345678, longitude: 1.2212345678, precision: 12.4 }))
      .toEqual({ latitude: "6.131235", longitude: "1.221235", precision: "12" });
  });
});
