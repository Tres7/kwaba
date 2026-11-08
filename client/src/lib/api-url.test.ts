import { describe, expect, it } from "vitest";
import { CheminRefuse, sansSlashFinal, sortDuChemin, urlProxy } from "./api-url";

// Security audit of 2026-11-07, leads 9 and 10: an id taken from the page's address must not lead elsewhere in the API
describe("sortDuChemin", () => {
  it.each([
    "/v1/concierge/conversations/../../voyages/invitations/CODE/?/messages/",
    "/v1/voyages/invitations/../../admin/lancement?/",
    "/v1/messaging/conversations/./read/",
    "/v1/x/%2e%2e/admin/",
    "/v1/x/.%2E/admin/",
    "/v1/x\\..\\admin/",
  ])("refuse un segment . ou .. (%s)", (url) => {
    expect(sortDuChemin(url)).toBe(true);
  });

  it.each([
    "/v1/concierge/conversations/1f0c2d7e-1a2b-4c3d-8e9f-0a1b2c3d4e5f/messages/",
    "/v1/voyages/invitations/..%2F..%2Fadmin%2Flancement%3F/",
    "/v1/hebergements/?q=../x",
    "/v1/hebergements/villa...plage/",
  ])("laisse passer un chemin normal ou encodé (%s)", (url) => {
    expect(sortDuChemin(url)).toBe(false);
  });
});

describe("urlProxy", () => {
  it("passe par le proxy, sans la barre finale", () => {
    expect(urlProxy("/v1/concierge/conversations/c1/messages/")).toBe("/api/proxy/v1/concierge/conversations/c1/messages");
    expect(sansSlashFinal("/v1/a/?b=1")).toBe("/v1/a?b=1");
  });

  it("refuse une adresse qui sortirait de la route demandée", () => {
    expect(() => urlProxy("/v1/concierge/conversations/../../voyages/invitations/X/?/messages/")).toThrow(CheminRefuse);
  });
});
