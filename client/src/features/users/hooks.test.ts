import { describe, expect, it } from "vitest";
import { accesEspaceHote } from "./hooks";

describe("accesEspaceHote", () => {
  it("ouvre l'espace aux hôtes, aux administrateurs et aux candidats", () => {
    expect(accesEspaceHote({ role: "hote", candidature_hote: "" })).toBe(true);
    expect(accesEspaceHote({ role: "admin", candidature_hote: "" })).toBe(true);
    expect(accesEspaceHote({ role: "voyageur", candidature_hote: "ouverte" })).toBe(true);
  });

  it("le ferme aux voyageurs, aux agents et aux candidatures refusées", () => {
    expect(accesEspaceHote({ role: "voyageur", candidature_hote: "" })).toBe(false);
    expect(accesEspaceHote({ role: "agent", candidature_hote: "" })).toBe(false);
    expect(accesEspaceHote({ role: "voyageur", candidature_hote: "refusee" })).toBe(false);
  });
});
