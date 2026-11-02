import { describe, expect, it } from "vitest";
import { lireRapportsCsp } from "./rapport-csp";

describe("lireRapportsCsp", () => {
  it("lit le format report-uri (Firefox, Safari)", () => {
    expect(lireRapportsCsp({
      "csp-report": { "document-uri": "https://kwa-ba.com/login", "effective-directive": "script-src-elem", "blocked-uri": "inline", "source-file": "https://kwa-ba.com/login", "line-number": 3 },
    })).toEqual([{ page: "https://kwa-ba.com/login", directive: "script-src-elem", bloque: "inline", source: "https://kwa-ba.com/login", ligne: 3 }]);
  });

  it("lit le format report-to (Chromium)", () => {
    expect(lireRapportsCsp([
      { type: "csp-violation", url: "https://kwa-ba.com/", body: { documentURL: "https://kwa-ba.com/", effectiveDirective: "img-src", blockedURL: "https://evil.example/x.png", sourceFile: "", lineNumber: 0 } },
    ])).toEqual([{ page: "https://kwa-ba.com/", directive: "img-src", bloque: "https://evil.example/x.png", source: "", ligne: 0 }]);
  });

  it("écarte requête et fragment, qui peuvent porter un email ou un jeton", () => {
    const [v] = lireRapportsCsp({
      "csp-report": { "document-uri": "https://kwa-ba.com/verify?email=ama%40example.tg#x", "blocked-uri": "https://evil.example/c?token=secret", "source-file": "not a url?x=1" },
    });
    expect(v.page).toBe("https://kwa-ba.com/verify");
    expect(v.bloque).toBe("https://evil.example/c");
    expect(v.source).toBe("not a url");
    expect(JSON.stringify(v)).not.toMatch(/ama|secret/);
  });

  it("masque le jeton d'un lien de signature", () => {
    const [v] = lireRapportsCsp({ "csp-report": { "document-uri": "https://kwa-ba.com/en/contrat/jeton-secret", "source-file": "https://kwa-ba.com/api/proxy/v1/contrats/signature/jeton-secret/pdf/" } });
    expect(v.page).toBe("https://kwa-ba.com/en/contrat/***");
    expect(v.source).toBe("https://kwa-ba.com/api/proxy/v1/contrats/signature/***/pdf/");
  });

  it("tronque les champs et ignore ceux qui ne sont pas du texte", () => {
    const [v] = lireRapportsCsp({ "csp-report": { "violated-directive": "x".repeat(5000), "blocked-uri": { a: 1 }, "line-number": "12" } });
    expect(v.directive).toHaveLength(200);
    expect(v.bloque).toBe("");
    expect(v.ligne).toBeNull();
  });

  it("garde seulement les violations de CSP d'un lot de rapports", () => {
    expect(lireRapportsCsp([{ type: "deprecation", body: {} }, { type: "csp-violation" }, null, 3])).toEqual([]);
  });

  it.each([[null], [undefined], [12], ["texte"], [{}], [{ "csp-report": "x" }]])("corps inattendu %j : rien", (corps) => {
    expect(lireRapportsCsp(corps)).toEqual([]);
  });
});
