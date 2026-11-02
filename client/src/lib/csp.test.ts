import { describe, expect, it, vi } from "vitest";
import { politiqueCsp, RAPPORTS_CSP } from "./csp";

const directive = (csp: string, nom: string) => csp.split("; ").find((d) => d.startsWith(`${nom} `)) ?? "";

describe("politiqueCsp", () => {
  it("avec nonce : le nonce de la réponse, et seuls ses scripts en chargent d'autres", () => {
    const scripts = directive(politiqueCsp("abc123"), "script-src");
    expect(scripts).toContain("'nonce-abc123'");
    expect(scripts).toContain("'strict-dynamic'");
  });

  it("avec nonce : jamais de « https: » seul, qui ouvrirait les anciens navigateurs à tous les sites", () => {
    expect(directive(politiqueCsp("abc123"), "script-src").split(" ")).not.toContain("https:");
  });

  it("sans nonce : aucun script en ligne, pas de rapports", () => {
    const csp = politiqueCsp();
    expect(directive(csp, "script-src").split(" ")).not.toContain("'unsafe-inline'");
    expect(directive(csp, "script-src").split(" ")).not.toContain("'strict-dynamic'");
    expect(csp).not.toContain("report-");
  });

  it("les styles en ligne restent permis, sans nonce pour ne pas les désactiver", () => {
    const styles = directive(politiqueCsp("abc123"), "style-src");
    expect(styles).toContain("'unsafe-inline'");
    expect(styles).not.toContain("nonce");
  });

  it("autorise la carte et rien de plus", () => {
    const csp = politiqueCsp("abc123");
    expect(directive(csp, "connect-src")).toContain("https://tiles.openfreemap.org");
    expect(directive(csp, "worker-src")).toBe("worker-src 'self'");
    expect(directive(csp, "frame-src")).not.toContain("maps.google.com");
  });

  it("en production, autorise Google Analytics sans ouvrir les images ni les envois à tous les sites", async () => {
    vi.stubEnv("NODE_ENV", "production");
    vi.resetModules();
    const { politiqueCsp: enProduction } = await import("./csp");
    vi.unstubAllEnvs();
    const csp = enProduction("abc123");
    expect(directive(csp, "script-src")).toContain("https://www.googletagmanager.com");
    expect(directive(csp, "connect-src")).toContain("https://*.google-analytics.com");
    expect(directive(csp, "connect-src")).toContain("https://*.analytics.google.com");
    expect(directive(csp, "img-src")).toContain("https://*.google-analytics.com");
    expect(directive(csp, "connect-src").split(" ")).not.toContain("https:");
    expect(directive(csp, "img-src").split(" ")).not.toContain("https:");
  });

  it("annonce le point de réception des rapports", () => {
    const csp = politiqueCsp("abc123");
    expect(directive(csp, "report-uri")).toBe(`report-uri ${RAPPORTS_CSP}`);
    expect(directive(csp, "report-to")).toBe("report-to csp");
  });

  it.each(["default-src 'self'", "frame-ancestors 'none'", "object-src 'none'", "base-uri 'self'", "form-action 'self'"])("garde %s", (attendue) => {
    expect(politiqueCsp("abc123").split("; ")).toContain(attendue);
    expect(politiqueCsp().split("; ")).toContain(attendue);
  });
});
