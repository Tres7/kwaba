import { describe, expect, it } from "vitest";
import { ETAPES, etapeAffichee, MAX_TITRE, MIN_DESCRIPTION, MIN_PHOTOS, peutContinuer, progressionPhases } from "./etapes";
import type { DonneesAnnonce } from "../brouillons";

const PHASE_1: DonneesAnnonce = {
  type: "villa", espace: "entier", city: "Lomé", location: "Baguida", latitude: 6.13, longitude: 1.22,
  max_guests: 4, surface_m2: 90, lits_doubles: 2,
};
const photos = (n: number) => Array.from({ length: n }, (_, i) => `https://kwa-ba.com/photos/${i}.jpg`);
const pret = (cle: string, d: DonneesAnnonce) => ETAPES.find((e) => e.cle === cle)!.pret!(d);

describe("etapeAffichee", () => {
  it("starts with the welcome screen", () => {
    expect(etapeAffichee(null, {}).cle).toBe("bienvenue");
    expect(etapeAffichee("inconnue", {}).cle).toBe("bienvenue");
  });

  it("shows the requested screen when everything before it is answered", () => {
    expect(etapeAffichee("equipements", PHASE_1).cle).toBe("equipements");
  });

  it("goes back to the first unanswered question", () => {
    expect(etapeAffichee("photos", { ...PHASE_1, city: "" }).cle).toBe("adresse");
    expect(etapeAffichee("fin", {}).cle).toBe("type");
  });

  it("does not block on the screen itself", () => {
    expect(etapeAffichee("type", {}).cle).toBe("type");
  });
});

describe("conditions pour continuer", () => {
  it("needs the city and the district", () => {
    expect(pret("adresse", { city: "Lomé", location: "  " })).toBe(false);
    expect(pret("adresse", { city: "Lomé", location: "Agoè" })).toBe(true);
  });

  it("needs a position on the map", () => {
    expect(pret("position", { latitude: 6.13 })).toBe(false);
    expect(pret("position", { latitude: 6.13, longitude: 1.22 })).toBe(true);
  });

  it("needs at least one bed and a surface", () => {
    expect(pret("capacite", { max_guests: 2, surface_m2: 40 })).toBe(false);
    expect(pret("capacite", { max_guests: 2, surface_m2: 40, canapes_lits: 1 })).toBe(true);
  });

  it(`needs ${MIN_PHOTOS} photos`, () => {
    expect(pret("photos", { images: photos(MIN_PHOTOS - 1) })).toBe(false);
    expect(pret("photos", { images: photos(MIN_PHOTOS) })).toBe(true);
  });

  it("keeps the title short", () => {
    expect(pret("titre", { name: "Villa" })).toBe(false);
    expect(pret("titre", { name: "Villa avec piscine à Baguida" })).toBe(true);
    expect(pret("titre", { name: "x".repeat(MAX_TITRE + 1) })).toBe(false);
  });

  it("asks for a real description", () => {
    expect(pret("description", { description: "Trop court" })).toBe(false);
    expect(pret("description", { description: "x".repeat(MIN_DESCRIPTION) })).toBe(true);
  });
});

describe("peutContinuer", () => {
  const description = ETAPES.find((e) => e.cle === "description")!;
  const reponse = { description: "Appelez-moi au 90 00 00 01 pour réserver cette belle villa." };

  it("stops on a field the API refuses, with the host still on that screen", () => {
    expect(peutContinuer(description, reponse, { description: ["Coordonnées refusées"] })).toBe(false);
  });

  it("goes on once the field is accepted", () => {
    expect(peutContinuer(description, reponse, {})).toBe(true);
  });

  it("ignores the errors of other screens", () => {
    expect(peutContinuer(description, reponse, { name: ["Refusé"] })).toBe(true);
  });

  it("needs the answer as well", () => {
    expect(peutContinuer(description, {}, {})).toBe(false);
  });
});

describe("progressionPhases", () => {
  it("is empty at the start", () => {
    expect(progressionPhases("bienvenue")).toEqual([0, 0, 0]);
  });

  it("fills the first phase as it goes", () => {
    const [premiere, deuxieme] = progressionPhases("adresse");
    expect(premiere).toBeGreaterThan(0);
    expect(premiere).toBeLessThan(1);
    expect(deuxieme).toBe(0);
  });

  it("has finished the first phase when the second one starts", () => {
    expect(progressionPhases("phase-2")[0]).toBe(1);
  });
});

describe("visuels", () => {
  it("every screen has its image", () => {
    for (const etape of ETAPES) expect(etape.visuel).toMatch(/^\/hote\/[a-z0-9-]+\.webp$/);
  });
});
