import { describe, expect, it } from "vitest";
import { guide, PAYS_GUIDES } from "./donnees";
import { RUBRIQUES } from "./types";

describe.each(PAYS_GUIDES)("guide %s", (pays) => {
  const fr = guide(pays, "fr")!;
  const en = guide(pays, "en")!;

  it("fills every heading in both languages", () => {
    for (const g of [fr, en]) {
      expect(g.titre && g.description && g.misAJour && g.avertissement).toBeTruthy();
      for (const cle of RUBRIQUES) {
        expect(g.rubriques[cle].titre, `${g.titre} › ${cle}`).toBeTruthy();
        expect(g.rubriques[cle].points.length, `${g.titre} › ${cle}`).toBeGreaterThan(0);
      }
    }
  });

  it("says the same in both languages: as many lines, the same links and services", () => {
    for (const cle of RUBRIQUES) {
      expect(en.rubriques[cle].points.length, cle).toBe(fr.rubriques[cle].points.length);
      expect(en.rubriques[cle].action?.href, cle).toBe(fr.rubriques[cle].action?.href);
      expect(en.rubriques[cle].sources?.length ?? 0, cle).toBe(fr.rubriques[cle].sources?.length ?? 0);
    }
  });

  it("closes every bold mark", () => {
    for (const g of [fr, en]) {
      for (const cle of RUBRIQUES) for (const point of g.rubriques[cle].points) expect(point.split("**").length % 2, point).toBe(1);
    }
  });
});

it("knows no other country yet", () => {
  expect(guide("benin", "fr")).toBeNull();
});
