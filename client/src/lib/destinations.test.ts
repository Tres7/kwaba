import { describe, expect, it } from "vitest";
import {
  cheminQuartier, cheminVille, logementsDu, quartierDeAdresse, quartierParSlug, slugDe, villeDuNom, villeParSlug,
} from "./destinations";
import { VILLES } from "./quartiers";

const lome = VILLES.find((v) => v.nom === "Lomé")!;

describe("destinations", () => {
  it("builds the addresses of the pages", () => {
    expect(slugDe("Bè Kpota")).toBe("be-kpota");
    expect(slugDe("Lom-Nava")).toBe("lom-nava");
    expect(cheminVille(lome)).toBe("/tg/lome");
    expect(cheminQuartier(lome, "Lomé 2")).toBe("/tg/lome/lome-2");
  });

  it("finds a city and a district from their address", () => {
    expect(villeParSlug("tg", "kpalime")?.nom).toBe("Kpalimé");
    expect(villeParSlug("bj", "lome")).toBeUndefined();
    expect(quartierParSlug(lome, "be-kpota")).toBe("Bè Kpota");
    expect(quartierParSlug(lome, "inconnu")).toBeUndefined();
  });

  it("gives each city and district a distinct address", () => {
    const villes = VILLES.map((v) => cheminVille(v));
    expect(new Set(villes).size).toBe(villes.length);
    for (const ville of VILLES) {
      const quartiers = ville.quartiers.map((q) => slugDe(q));
      expect(new Set(quartiers).size).toBe(quartiers.length);
    }
  });

  it("recognises the city typed by a host", () => {
    expect(villeDuNom(" LOME ")).toBe(lome);
    expect(villeDuNom("Tsévié")).toBeUndefined();
  });

  it("puts a listing in one district, by whole words", () => {
    expect(quartierDeAdresse(lome, "Bè Kpota, rue 12")).toBe("Bè Kpota");
    expect(quartierDeAdresse(lome, "Bè")).toBe("Bè");
    expect(quartierDeAdresse(lome, "tokoin casablanca")).toBe("Tokoin");
    expect(quartierDeAdresse(lome, "Bèniglato")).toBeUndefined();
  });

  it("selects the listings of a country, a city or a district", () => {
    const logements = [
      { id: "a", city: "Lome", location: "Tokoin Hôpital" },
      { id: "b", city: "Lomé", location: "Bè Kpota" },
      { id: "c", city: "Kpalimé", location: "Nyivémé" },
      { id: "d", city: "Cotonou", location: "Fidjrossè" },
    ];
    const ids = (liste: { id: string }[]) => liste.map((h) => h.id);
    expect(ids(logementsDu(logements, { pays: "tg" }))).toEqual(["a", "b", "c"]);
    expect(ids(logementsDu(logements, { pays: "tg", ville: lome }))).toEqual(["a", "b"]);
    expect(ids(logementsDu(logements, { pays: "tg", ville: lome, quartier: "Tokoin" }))).toEqual(["a"]);
    expect(ids(logementsDu(logements, { pays: "tg", ville: lome, quartier: "Bè" }))).toEqual([]);
  });
});
