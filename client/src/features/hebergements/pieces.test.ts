import { describe, expect, it } from "vitest";
import { codesPieces, libellePiece, photosParPiece } from "./pieces";

const t = (cle: string, valeurs?: Record<string, number>) => (valeurs ? `${cle} ${valeurs.numero}` : cle);

describe("codesPieces", () => {
  it("numbers the bedrooms and bathrooms", () => {
    const codes = codesPieces(2, 2);
    expect(codes.slice(0, 2)).toEqual(["chambre_1", "chambre_2"]);
    expect(codes).toContain("salle_de_bain_2");
    expect(codes).not.toContain("piece_principale");
  });

  it("gives a studio a main room and always one bathroom", () => {
    const codes = codesPieces(0, 0);
    expect(codes[0]).toBe("piece_principale");
    expect(codes.filter((c) => c.startsWith("salle_de_bain"))).toEqual(["salle_de_bain_1"]);
  });
});

describe("libellePiece", () => {
  it("passes the number of a bedroom", () => {
    expect(libellePiece("chambre_3", t)).toBe("chambre 3");
    expect(libellePiece("salon", t)).toBe("salon");
  });
});

describe("photosParPiece", () => {
  it("groups the photos in the order of a visit, the ones without a room last", () => {
    const groupes = photosParPiece(["a", "b", "c", "d"], { a: "salon", b: "chambre_1", d: "salon" });
    expect(groupes).toEqual([["chambre_1", ["b"]], ["salon", ["a", "d"]], ["", ["c"]]]);
  });
});
