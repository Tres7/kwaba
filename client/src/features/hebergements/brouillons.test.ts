import { describe, expect, it } from "vitest";
import { completude, photoDepuisUrl, type DonneesAnnonce } from "./brouillons";

const COMPLETE: DonneesAnnonce = {
  name: "Villa Océane", city: "Lomé", price_per_night: 85000, latitude: 6.1375, longitude: 1.2123,
  point_repere: "Derrière la pharmacie", salles_de_bain: 1, lits_doubles: 2, petit_dejeuner: "non", images: ["https://kwa-ba.com/photos/a.jpg"],
};

describe("completude", () => {
  it("empty draft: nothing filled in, everything missing", () => {
    expect(completude({})).toEqual({
      pourcentage: 0,
      manquants: ["titre", "ville", "prix", "position", "pointRepere", "sallesDeBain", "lits", "petitDejeuner", "photos"],
    });
  });

  it("complete listing: 100 %, nothing missing", () => {
    expect(completude(COMPLETE)).toEqual({ pourcentage: 100, manquants: [] });
  });

  it("rounds the share of the criteria filled in", () => {
    expect(completude({ ...COMPLETE, images: [], point_repere: " " })).toEqual({ pourcentage: 78, manquants: ["pointRepere", "photos"] });
    expect(completude({ name: "Studio" }).pourcentage).toBe(11);
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

describe("photoDepuisUrl", () => {
  const id = "3f2c1b6a-9d4e-4f7a-8c21-5e6a7b8c9d0e";

  it("reads the id of an uploaded photo, on R2 as on the local disk", () => {
    expect(photoDepuisUrl(`https://kwa-ba.com/photos/hebergements/aaaa/${id}.jpg`)).toBe(id);
    expect(photoDepuisUrl(`http://localhost:8000/media/hebergements/aaaa/${id}.jpg`)).toBe(id);
  });

  it("ignores any other image", () => {
    expect(photoDepuisUrl("https://images.unsplash.com/photo-1.jpg")).toBeNull();
  });
});
