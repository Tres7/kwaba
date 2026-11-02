import { afterEach, describe, expect, it, vi } from "vitest";
import { ouvrirSession } from "./connexion";

// next-auth imports next/server, which only resolves inside Next
vi.mock("next-auth", () => ({ CredentialsSignin: class extends Error { code = "credentials"; } }));

const requete = (entetes: Record<string, string> = {}) => new Request("https://kwa-ba.com/api/auth/callback/google-id-token", { headers: entetes });

function reponseApi(statut: number, corps: unknown) {
  const appel = vi.fn(async (..._args: Parameters<typeof fetch>) => new Response(JSON.stringify(corps), { status: statut }));
  vi.stubGlobal("fetch", appel);
  return appel;
}

const JETONS = {
  access: "acces",
  refresh: "rafraichissement",
  user: { id: "1", email: "ama@example.tg", first_name: "Ama", last_name: "Kossi", role: "voyageur", avatar_url: null, is_verified: true, is_active: true },
};

describe("ouvrirSession", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("garde les jetons pour la session et l'identité lue dans la réponse de l'API", async () => {
    reponseApi(200, JETONS);
    await expect(ouvrirSession("/v1/auth/google/", { id_token: "x" }, requete())).resolves.toEqual({
      id: "1", name: "Ama Kossi", email: "ama@example.tg", image: null, accessToken: "acces", refreshToken: "rafraichissement", role: "voyageur",
    });
  });

  it("transmet l'adresse reçue de nginx", async () => {
    const appel = reponseApi(200, JETONS);
    await ouvrirSession("/v1/auth/google/", {}, requete({ "x-forwarded-for": "1.2.3.4, 41.207.0.1" }));
    const init = appel.mock.calls[0][1] as RequestInit;
    expect((init.headers as Record<string, string>)["X-Forwarded-For"]).toBe("1.2.3.4, 41.207.0.1");
  });

  it.each([
    [403, { code: "inactive" }, "inactive"],
    [400, { code: "invalid_code" }, "invalid_code"],
    [400, { code: "already_verified" }, "already_verified"],
    [429, { detail: "Request was throttled." }, "too_many_attempts"],
    [429, { code: "too_many_attempts" }, "too_many_attempts"],
    [401, { detail: "Identifiants invalides." }, "refus"],
    [200, {}, "serveur"],
  ])("réponse %i %j : code %s pour le formulaire", async (statut, corps, code) => {
    reponseApi(statut, corps);
    await expect(ouvrirSession("/v1/auth/login/", {}, requete())).rejects.toMatchObject({ code });
  });

  it("API injoignable : code serveur", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new TypeError("fetch failed"); }));
    await expect(ouvrirSession("/v1/auth/login/", {}, requete())).rejects.toMatchObject({ code: "serveur" });
  });
});
