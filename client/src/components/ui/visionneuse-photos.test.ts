import { describe, expect, it } from "vitest";
import { bornerPhoto, photosAcharger, voisines } from "./visionneuse-photos";

// KB-99: the viewer loads the photo shown and the next one, never the whole gallery at once
describe("photosAcharger", () => {
  it("charge la photo ouverte et ses deux voisines, pas le reste de la galerie", () => {
    expect([...photosAcharger(new Set(), 5, 12)].sort((a, b) => a - b)).toEqual([4, 5, 6]);
  });

  it("garde les photos déjà chargées pour revenir en arrière sans cadre vide", () => {
    const apres = photosAcharger(new Set([0, 1]), 2, 12);
    expect([...apres].sort((a, b) => a - b)).toEqual([0, 1, 2, 3]);
  });

  it("rend le même ensemble quand rien ne manque (pas de rendu inutile pendant le défilement)", () => {
    const chargees = new Set([3, 4, 5]);
    expect(photosAcharger(chargees, 4, 12)).toBe(chargees);
  });

  it("ne sort pas de la galerie à la première et à la dernière photo", () => {
    expect(voisines(0, 12)).toEqual([0, 1]);
    expect(voisines(11, 12)).toEqual([10, 11]);
    expect(voisines(0, 1)).toEqual([0]);
  });
});

describe("bornerPhoto", () => {
  it("s'arrête à la première et à la dernière photo, sans boucler", () => {
    expect(bornerPhoto(-1, 12)).toBe(0);
    expect(bornerPhoto(12, 12)).toBe(11);
    expect(bornerPhoto(4, 12)).toBe(4);
  });
});
