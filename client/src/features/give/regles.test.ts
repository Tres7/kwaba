import { describe, expect, it } from "vitest";
import { calculerDon, dateReversement } from "./regles";

describe("calculerDon", () => {
  it("le donateur couvre les frais : l'ONG reçoit tout le montant", () => {
    expect(calculerDon(1000, true, 0.03)).toEqual({ frais: 31, total: 1031, montantOng: 1000 });
  });

  it("les frais sont pris sur le don sinon", () => {
    expect(calculerDon(1000, false, 0.03)).toEqual({ frais: 30, total: 1000, montantOng: 970 });
  });
});

describe("dateReversement", () => {
  it("tombe le mois suivant, y compris en décembre", () => {
    expect(dateReversement(15, new Date(2026, 11, 20))).toEqual(new Date(2027, 0, 15));
  });
});
