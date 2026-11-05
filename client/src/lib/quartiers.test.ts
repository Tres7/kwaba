import { describe, expect, it } from "vitest";
import { quartiersCorrespondants, quartiersDe, VILLES } from "./quartiers";

describe("quartiers", () => {
  it("finds the districts of a city typed without accents", () => {
    expect(quartiersDe("lome")).toContain("Tokoin");
    expect(quartiersDe(" Kpalime ")).toContain("Nyivémé");
    expect(quartiersDe("Cotonou")).toEqual([]);
  });

  it("suggests a district with its city, in every city", () => {
    expect(quartiersCorrespondants("chamin")).toEqual([{ nom: "Chaminade", ville: "Kara" }]);
    expect(quartiersCorrespondants("zongo").map((q) => `${q.nom}, ${q.ville}`)).toEqual(["Zongo, Kpalimé", "Zongomè, Aného", "Zongo, Sokodé"]);
    expect(quartiersCorrespondants("  ")).toEqual([]);
  });

  it("lists each district once per city", () => {
    for (const ville of VILLES) expect(new Set(ville.quartiers).size).toBe(ville.quartiers.length);
  });
});
