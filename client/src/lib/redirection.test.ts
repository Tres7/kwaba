import { describe, expect, it } from "vitest";
import { safeCallback } from "./redirection";

describe("safeCallback", () => {
  it.each([
    ["/", "/"],
    ["/reservation/12?arrivee=2026-11-02&voyageurs=2", "/reservation/12?arrivee=2026-11-02&voyageurs=2"],
    ["/give/ecole#don", "/give/ecole#don"],
    ["/recherche?retour=https://evil.com", "/recherche?retour=https://evil.com"],
  ])("garde l'adresse interne %s", (url, attendu) => {
    expect(safeCallback(url)).toBe(attendu);
  });

  it.each([
    [null],
    [""],
    ["//evil.com"],
    ["https://evil.com"],
    ["javascript:alert(1)"],
    ["data:text/html,<script>alert(1)</script>"],
    // Backslash read as a slash by the browser
    ["/\\evil.com"],
    ["\\\\evil.com"],
    ["/\\/evil.com"],
    // Tabs and line breaks dropped by the browser
    ["/\t/evil.com"],
    ["/\n/evil.com"],
    ["\t//evil.com"],
    // Stays on the site once resolved, but its path is an external address
    ["/.//evil.com"],
    ["/..//evil.com"],
    ["/%2e//evil.com"],
    ["/recherche/..//evil.com"],
  ])("refuse %j", (url) => {
    expect(safeCallback(url)).toBe("/");
  });

  it("laisse un antislash encodé sur le site", () => {
    const resultat = safeCallback("/%5Cevil.com");
    expect(new URL(resultat, "https://kwa-ba.com").origin).toBe("https://kwa-ba.com");
  });
});
