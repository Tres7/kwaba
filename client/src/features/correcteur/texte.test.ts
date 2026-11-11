import { describe, expect, it } from "vitest";
import { cleFaute, corriger, fauteA, fautesEnPlace, morceaux, sansChoix, toutCorriger } from "./texte";
import type { Faute } from "./types";

const faute = (debut: number, extrait: string, remplacements: string[] = [], regle = "FR_SPELLING_RULE"): Faute => ({
  debut, longueur: extrait.length, extrait, type: "orthographe", message: "", remplacements, regle,
});

const TEXTE = "Une mason avec pisine";
const MASON = faute(4, "mason", ["maison"]);
const PISINE = faute(15, "pisine", ["piscine", "pisciné"]);

describe("fautes en place", () => {
  it("garde les fautes encore à leur place, dans l'ordre du texte", () => {
    expect(fautesEnPlace(TEXTE, [PISINE, MASON], new Set())).toEqual([MASON, PISINE]);
  });

  it("écarte une faute dont le texte a changé depuis la vérification", () => {
    expect(fautesEnPlace("Une maison avec pisine", [MASON, PISINE], new Set())).toEqual([]);
  });

  it("écarte les fautes ignorées et celles qui en chevauchent une autre", () => {
    expect(fautesEnPlace(TEXTE, [MASON, PISINE], new Set([cleFaute(PISINE)]))).toEqual([MASON]);
    expect(fautesEnPlace(TEXTE, [MASON, faute(4, "mason avec", [], "AUTRE")], new Set())).toEqual([MASON]);
  });

  it("compte un emoji pour deux, comme l'API", () => {
    const texte = "Top 🌴 mason";
    expect(fautesEnPlace(texte, [faute(7, "mason")], new Set())).toHaveLength(1);
  });
});

describe("corrections", () => {
  it("remplace une faute et décale celles qui suivent", () => {
    const { texte, fautes } = corriger(TEXTE, [MASON, PISINE], MASON, "maison");
    expect(texte).toBe("Une maison avec pisine");
    expect(fautes).toEqual([{ ...PISINE, debut: 16 }]);
    expect(fautesEnPlace(texte, fautes, new Set())).toHaveLength(1);
  });

  it("laisse choisir l'hôte quand la grammaire propose plusieurs corrections", () => {
    const texte = "Les chambre sont climatisé";
    const accord = { ...faute(0, "Les chambre", ["La chambre", "Les chambres"], "D_N"), type: "grammaire" as const };
    const participe = { ...faute(17, "climatisé", ["climatisée"], "ETRE_VPPA"), type: "grammaire" as const };
    expect([accord, participe].map(sansChoix)).toEqual([false, true]);
    expect(toutCorriger(texte, [accord, participe])).toEqual({ texte: "Les chambre sont climatisée", fautes: [accord] });
  });

  it("corrige tout avec la première proposition, sans décaler les positions", () => {
    const sansProposition = faute(10, "avec");
    const { texte, fautes } = toutCorriger(TEXTE, [MASON, sansProposition, PISINE]);
    expect(texte).toBe("Une maison avec piscine");
    // The mistake without a correction stays, moved by the correction before it
    expect(fautes).toEqual([{ ...sansProposition, debut: 11 }]);
    expect(fautesEnPlace(texte, fautes, new Set())).toHaveLength(1);
  });
});

describe("calque de soulignement", () => {
  it("coupe le texte en morceaux simples et en fautes", () => {
    expect(morceaux(TEXTE, [MASON, PISINE])).toEqual([
      { texte: "Une " }, { texte: "mason", faute: MASON }, { texte: " avec " }, { texte: "pisine", faute: PISINE },
    ]);
    expect(morceaux("Une mason.", [MASON]).at(-1)).toEqual({ texte: "." });
  });

  it("trouve la faute sous le curseur, bords compris", () => {
    expect(fauteA([MASON, PISINE], 4)).toBe(MASON);
    expect(fauteA([MASON, PISINE], 9)).toBe(MASON);
    expect(fauteA([MASON, PISINE], 12)).toBeUndefined();
    expect(fauteA([MASON], null)).toBeUndefined();
  });
});
