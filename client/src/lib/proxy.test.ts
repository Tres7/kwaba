import { describe, expect, it } from "vitest";
import { cheminApi, entetesVersApi, entetesVersNavigateur, origineAutorisee } from "./proxy";

describe("cheminApi", () => {
  it("accepte une route de l'API et remet le slash final", () => {
    expect(cheminApi(["v1", "hebergements", "12"])).toBe("v1/hebergements/12/");
  });

  it("encode chaque segment", () => {
    expect(cheminApi(["v1", "contrats", "a b?c"])).toBe("v1/contrats/a%20b%3Fc/");
  });

  it.each([
    [["admin", "login"]],
    [["v1"]],
    [["v2", "x"]],
    [["v1", "..", "admin"]],
    [["v1", ".", "x"]],
    [["v1", "", "x"]],
    [["v1", "x/../../admin"]],
    [["v1", "x\\..\\admin"]],
  ])("refuse %j", (segments) => {
    expect(cheminApi(segments)).toBeNull();
  });
});

describe("origineAutorisee", () => {
  it("laisse passer les lectures sans origine", () => {
    expect(origineAutorisee("GET", null, "kwa-ba.com")).toBe(true);
  });

  it("accepte une écriture venant du site", () => {
    expect(origineAutorisee("POST", "https://kwa-ba.com", "kwa-ba.com")).toBe(true);
    expect(origineAutorisee("DELETE", "http://localhost:3000", "localhost:3000")).toBe(true);
  });

  it.each([
    ["https://evil.com", "kwa-ba.com"],
    ["https://blog.kwa-ba.com", "kwa-ba.com"],
    ["https://kwa-ba.com.evil.com", "kwa-ba.com"],
    ["null", "kwa-ba.com"],
    [null, "kwa-ba.com"],
    ["https://kwa-ba.com", null],
  ])("refuse une écriture depuis %s", (origine, hote) => {
    expect(origineAutorisee("POST", origine, hote)).toBe(false);
  });
});

describe("entetesVersApi", () => {
  const api = new URL("https://kwa-ba.com/api");

  it("ajoute le jeton et présente l'hôte public de l'API", () => {
    const entetes = entetesVersApi(new Headers({ host: "client:3000" }), "jeton", api);
    expect(entetes.get("authorization")).toBe("Bearer jeton");
    expect(entetes.get("x-forwarded-host")).toBe("kwa-ba.com");
    expect(entetes.get("x-forwarded-proto")).toBe("https");
  });

  it("garde la chaîne d'adresses reçue de nginx", () => {
    const entetes = entetesVersApi(new Headers({ "x-forwarded-for": "1.2.3.4, 41.207.0.1" }), undefined, api);
    expect(entetes.get("x-forwarded-for")).toBe("1.2.3.4, 41.207.0.1");
  });

  it("ne transmet ni les cookies ni un jeton venu du navigateur", () => {
    const entetes = entetesVersApi(new Headers({ cookie: "session=secret", authorization: "Bearer forge" }), undefined, api);
    expect(entetes.get("cookie")).toBeNull();
    expect(entetes.get("authorization")).toBeNull();
  });
});

describe("entetesVersNavigateur", () => {
  it("retire ce qui est propre à la liaison entre les serveurs", () => {
    const entetes = entetesVersNavigateur(new Headers({
      "content-type": "text/event-stream",
      "x-accel-buffering": "no",
      "retry-after": "60",
      "set-cookie": "a=b",
      "strict-transport-security": "max-age=1",
    }));
    expect(entetes.get("content-type")).toBe("text/event-stream");
    expect(entetes.get("x-accel-buffering")).toBe("no");
    expect(entetes.get("retry-after")).toBe("60");
    expect(entetes.get("set-cookie")).toBeNull();
    expect(entetes.get("strict-transport-security")).toBeNull();
  });
});
