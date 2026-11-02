import { describe, expect, it } from "vitest";
import { definirLangue, formats, langue } from "./utils";

describe("formats", () => {
  it("garde la langue demandée, sans état partagé entre les deux", () => {
    const fr = formats("fr");
    const en = formats("en");
    expect(fr.selon({ fr: "bonjour", en: "hello" })).toBe("bonjour");
    expect(en.selon({ fr: "bonjour", en: "hello" })).toBe("hello");
    expect(fr.selon({ fr: "bonjour", en: "hello" })).toBe("bonjour");
    expect(fr.langue()).toBe("fr");
    expect(en.langue()).toBe("en");
  });

  it("une langue inconnue retombe sur le français", () => {
    expect(formats("de").langue()).toBe("fr");
  });

  it("montants séparés selon la langue", () => {
    expect(formats("fr").formatFcfa(25000)).toBe("25 000 FCFA");
    expect(formats("en").formatFcfa(25000)).toBe("25,000 FCFA");
  });

  it("dates dans la langue demandée", () => {
    expect(formats("fr").formatDate("2026-11-02T12:00:00")).toBe("2 nov. 2026");
    expect(formats("en").formatDate("2026-11-02T12:00:00")).toBe("2 Nov 2026");
    expect(formats("en").formatDate("")).toBe("-");
  });

  it("date de vol lisible", () => {
    expect(formats("fr").dateVol("2026-11-02T14:30")).toBe("lundi 2 novembre à 14 h 30");
    expect(formats("en").dateVol("2026-11-02T14:30")).toBe("Monday 2 November at 14:30");
  });

  it("mois et année", () => {
    expect(formats("fr").moisAnnee("2026-11-01")).toBe("novembre 2026");
    expect(formats("en").moisAnnee("2026-11-01")).toBe("November 2026");
  });

  it("libellés traduits, code rendu tel quel s'il est inconnu, liste des codes conservée", () => {
    const { TYPE_LABELS, ROLE_LABELS } = formats("en");
    expect(TYPE_LABELS.maison).toBe("House");
    expect(TYPE_LABELS.inconnu).toBe("inconnu");
    expect(ROLE_LABELS.voyageur).toBe("Traveller");
    expect(Object.keys(TYPE_LABELS)).toContain("hotel");
  });
});

describe("definirLangue", () => {
  it("sans navigateur, ne change rien : plusieurs requêtes sont rendues en même temps", () => {
    definirLangue("en");
    expect(langue()).toBe("fr");
  });
});
