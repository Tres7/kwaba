import { describe, expect, it } from "vitest";
import { ETAPES, etapeAffichee, etapeVoisine, MAX_TITRE, MIN_DESCRIPTION, MIN_PHOTOS, peutContinuer, progressionPhases, type Conditions } from "./etapes";
import type { DonneesAnnonce } from "../brouillons";

const PHASE_1: DonneesAnnonce = {
  type: "villa", city: "Lomé", location: "Baguida", point_repere: "Derrière la pharmacie", latitude: 6.13, longitude: 1.22,
  max_guests: 4, chambres: 2, salles_de_bain: 1, lits_doubles: 2,
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
    expect(etapeAffichee("recapitulatif", {}).cle).toBe("type");
  });

  it("does not block on the screen itself", () => {
    expect(etapeAffichee("type", {}).cle).toBe("type");
  });
});

describe("conditions pour continuer", () => {
  it("needs the city, the district and a landmark", () => {
    expect(pret("adresse", { city: "Lomé", location: "  ", point_repere: "Derrière le CHU" })).toBe(false);
    expect(pret("adresse", { city: "Lomé", location: "Agoè" })).toBe(false);
    expect(pret("adresse", { city: "Lomé", location: "Agoè", point_repere: "Derrière le CHU" })).toBe(true);
  });

  it("needs a position on the map", () => {
    expect(pret("position", { latitude: 6.13 })).toBe(false);
    expect(pret("position", { latitude: 6.13, longitude: 1.22 })).toBe(true);
  });

  it("needs bedrooms, a bathroom and at least one bed, but no surface", () => {
    const studio = { max_guests: 2, chambres: 0, salles_de_bain: 1 };
    expect(pret("capacite", studio)).toBe(false);
    expect(pret("capacite", { ...studio, canapes_lits: 1 })).toBe(true);
    expect(pret("capacite", { ...studio, canapes_lits: 1, salles_de_bain: 0 })).toBe(false);
    expect(pret("capacite", { ...studio, canapes_lits: 1, max_guests: 21 })).toBe(false);
  });

  it(`needs ${MIN_PHOTOS} photos`, () => {
    const pieces = (urls: string[]) => Object.fromEntries(urls.map((url) => [url, "salon"]));
    expect(pret("photos", { images: photos(MIN_PHOTOS - 1), legendes_photos: pieces(photos(MIN_PHOTOS - 1)) })).toBe(false);
    expect(pret("photos", { images: photos(MIN_PHOTOS), legendes_photos: pieces(photos(MIN_PHOTOS)) })).toBe(true);
    // Every photo needs its room
    expect(pret("photos", { images: photos(MIN_PHOTOS), legendes_photos: pieces(photos(MIN_PHOTOS - 1)) })).toBe(false);
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

const CONDITIONS: Conditions = {
  photos: true, photos_du_compte: true, attestation: true, telephone: true, identite: "soumise", versement: true,
  preinscription: true, contrat_a_signer: false, bloquants: [],
};
const etape = (cle: string) => ETAPES.find((e) => e.cle === cle)!;

describe("etapes qui dependent de l'API", () => {
  it("waits for the API before going on", () => {
    expect(peutContinuer(etape("telephone"), {}, {}, undefined)).toBe(false);
    expect(peutContinuer(etape("telephone"), {}, {}, { ...CONDITIONS, telephone: false })).toBe(false);
    expect(peutContinuer(etape("telephone"), {}, {}, CONDITIONS)).toBe(true);
  });

  it("accepts an identity document sent, not a refused one", () => {
    expect(peutContinuer(etape("identite"), {}, {}, CONDITIONS)).toBe(true);
    expect(peutContinuer(etape("identite"), {}, {}, { ...CONDITIONS, identite: "refusee" })).toBe(false);
  });

  it("refuses to send while something blocks", () => {
    expect(peutContinuer(etape("recapitulatif"), {}, {}, { ...CONDITIONS, bloquants: ["versement"] })).toBe(false);
    expect(peutContinuer(etape("recapitulatif"), {}, {}, CONDITIONS)).toBe(true);
  });

  it("skips the terms when there is nothing to accept or sign", () => {
    expect(etapeVoisine(etape("versement"), 1, CONDITIONS)?.cle).toBe("recapitulatif");
    expect(etapeVoisine(etape("recapitulatif"), -1, CONDITIONS)?.cle).toBe("versement");
  });

  it("shows the terms when the pre-registration is required", () => {
    expect(etapeVoisine(etape("versement"), 1, { ...CONDITIONS, preinscription: false })?.cle).toBe("contrat");
  });

  it("shows the screen while the API has not answered", () => {
    expect(etapeVoisine(etape("versement"), 1, undefined)?.cle).toBe("contrat");
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

  it("goes on through the third phase", () => {
    expect(progressionPhases("versement")[2]).toBeGreaterThan(0.5);
  });
});

describe("pictogrammes", () => {
  it("changes on every screen, so that the host sees the step move on", () => {
    ETAPES.slice(1).forEach((etape, i) => expect(etape.picto, etape.cle).not.toBe(ETAPES[i].picto));
  });
});

describe("hotels, aparthotels and guesthouses", () => {
  const HOTEL: DonneesAnnonce = { ...PHASE_1, type: "chambre_hotel" };
  const etape = (cle: string) => ETAPES.find((e) => e.cle === cle)!;
  const double = { nom: "Double standard", prix_nuit: 35000, quantite: 80, capacite: 2 };

  it("give their room types instead of the beds of a house, and no separate price", () => {
    expect(etapeVoisine(etape("position"), 1, undefined, HOTEL)?.cle).toBe("chambres");
    expect(etapeVoisine(etape("chambres"), 1, undefined, HOTEL)?.cle).toBe("phase-2");
    expect(etapeVoisine(etape("phase-3"), 1, undefined, HOTEL)?.cle).toBe("regles");
    expect(etapeVoisine(etape("position"), 1, undefined, PHASE_1)?.cle).toBe("capacite");
  });

  it("need every room type complete", () => {
    expect(pret("chambres", { ...HOTEL, types_chambres: [] })).toBe(false);
    expect(pret("chambres", { ...HOTEL, types_chambres: [double, { ...double, nom: " " }] })).toBe(false);
    expect(pret("chambres", { ...HOTEL, types_chambres: [double, { ...double, nom: "Suite", quantite: 10 }] })).toBe(true);
  });

  it("come back to their rooms, never to the beds of a house", () => {
    expect(etapeAffichee("capacite", HOTEL).cle).toBe("chambres");
    expect(etapeAffichee("photos", { ...HOTEL, types_chambres: [double] }).cle).toBe("photos");
  });
});
