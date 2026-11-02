import { readdirSync } from "node:fs";
import { join, relative } from "node:path";
import { describe, expect, it } from "vitest";
import { cheminMesurable } from "./mesure-audience";

const APP = join(__dirname, "..", "app", "[locale]", "(main)");
const PUBLIQUES = ["/hebergements/secret", "/give/secret"];

/** Addresses of the site's dynamic pages, with "secret" in place of their parameters. */
function pagesDynamiques(dossier = APP): string[] {
  return readdirSync(dossier, { withFileTypes: true }).flatMap((entree) => {
    if (!entree.isDirectory()) return [];
    const chemin = join(dossier, entree.name);
    const adresse = `/${relative(APP, chemin).replace(/\\/g, "/")}`;
    const ici = entree.name.startsWith("[") ? [adresse.replace(/\[[^\]]+\]/g, "secret")] : [];
    return [...ici, ...pagesDynamiques(chemin)];
  });
}

describe("cheminMesurable", () => {
  it("le test voit bien les pages dynamiques", () => {
    expect(pagesDynamiques()).toEqual(expect.arrayContaining(["/contrat/secret", "/hebergements/secret"]));
    expect(pagesDynamiques().length).toBeGreaterThan(10);
  });

  it.each(pagesDynamiques().filter((p) => !PUBLIQUES.includes(p)))("aucun identifiant de %s ne part chez Google", (page) => {
    expect(cheminMesurable(page)).not.toContain("secret");
    expect(cheminMesurable(`/en${page}`)).not.toContain("secret");
  });

  it.each(PUBLIQUES)("%s reste lisible dans les statistiques", (page) => {
    expect(cheminMesurable(page)).toBe(page);
  });

  it("garde les pages sans identifiant", () => {
    expect(cheminMesurable("/")).toBe("/");
    expect(cheminMesurable("/en/recherche")).toBe("/en/recherche");
    expect(cheminMesurable("/location")).toBe("/location");
  });

  it("masque le lien d'invitation sans garder de morceau", () => {
    expect(cheminMesurable("/together/rejoindre/AB12CD")).toBe("/together/rejoindre/:id");
    expect(cheminMesurable("/en/contrat/jeton-long/suite")).toBe("/en/contrat/:id/suite");
  });

  it("ne mesure pas les pages de l'équipe", () => {
    expect(cheminMesurable("/backoffice")).toBeNull();
    expect(cheminMesurable("/backoffice/annonces")).toBeNull();
    expect(cheminMesurable("/agent/a-faire")).toBeNull();
  });

  it("ne confond pas une page publique avec une page de l'équipe", () => {
    expect(cheminMesurable("/agents-de-voyage")).toBe("/agents-de-voyage");
  });
});
