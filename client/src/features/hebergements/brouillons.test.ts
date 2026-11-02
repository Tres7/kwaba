import { describe, expect, it } from "vitest";
import { completude, type DonneesAnnonce } from "./brouillons";

const COMPLETE: DonneesAnnonce = {
  name: "Villa Océane", city: "Lomé", price_per_night: 85000, latitude: 6.1375, longitude: 1.2123,
  surface_m2: 140, lits_doubles: 2, petit_dejeuner: "non", images: ["https://kwa-ba.com/photos/a.jpg"],
};

describe("completude", () => {
  it("empty draft: nothing filled in, everything missing", () => {
    expect(completude({})).toEqual({
      pourcentage: 0,
      manquants: ["titre", "ville", "prix", "position", "surface", "lits", "petitDejeuner", "photos"],
    });
  });

  it("complete listing: 100 %, nothing missing", () => {
    expect(completude(COMPLETE)).toEqual({ pourcentage: 100, manquants: [] });
  });

  it("rounds the share of the criteria filled in", () => {
    expect(completude({ ...COMPLETE, images: [], surface_m2: null })).toEqual({ pourcentage: 75, manquants: ["surface", "photos"] });
    expect(completude({ name: "Studio" }).pourcentage).toBe(13);
  });

  it("blank title, zero price and a single coordinate count as missing", () => {
    const { manquants } = completude({ ...COMPLETE, name: "  ", price_per_night: 0, longitude: null });
    expect(manquants).toEqual(["titre", "prix", "position"]);
  });

  it("breakfast as an option requires its price", () => {
    expect(completude({ ...COMPLETE, petit_dejeuner: "option" }).manquants).toEqual(["petitDejeuner"]);
    expect(completude({ ...COMPLETE, petit_dejeuner: "option", petit_dejeuner_prix: 3000 }).manquants).toEqual([]);
  });
});
