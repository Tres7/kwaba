import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { renouvelerUneFois } from "./renouvellement";

const reussi = (r: string) => r === "nouveau";
let numero = 0;
const jeton = () => `jeton-${++numero}`;

describe("renouvelerUneFois", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("deux onglets en même temps n'envoient le jeton qu'une fois", async () => {
    const renouveler = vi.fn().mockResolvedValue("nouveau");
    const cle = jeton();
    const [a, b] = await Promise.all([renouvelerUneFois(cle, renouveler, reussi), renouvelerUneFois(cle, renouveler, reussi)]);
    expect(renouveler).toHaveBeenCalledTimes(1);
    expect([a, b]).toEqual(["nouveau", "nouveau"]);
  });

  it("un onglet juste après reçoit la même réponse", async () => {
    const renouveler = vi.fn().mockResolvedValue("nouveau");
    const cle = jeton();
    await renouvelerUneFois(cle, renouveler, reussi);
    vi.advanceTimersByTime(10_000);
    await expect(renouvelerUneFois(cle, renouveler, reussi)).resolves.toBe("nouveau");
    expect(renouveler).toHaveBeenCalledTimes(1);
  });

  it("oublie le résultat après la fenêtre, pour ne pas garder les jetons en mémoire", async () => {
    const renouveler = vi.fn().mockResolvedValue("nouveau");
    const cle = jeton();
    await renouvelerUneFois(cle, renouveler, reussi);
    vi.advanceTimersByTime(31_000);
    await renouvelerUneFois(cle, renouveler, reussi);
    expect(renouveler).toHaveBeenCalledTimes(2);
  });

  it("réessaie après un renouvellement qui n'a pas abouti", async () => {
    const renouveler = vi.fn().mockResolvedValueOnce("inchange").mockResolvedValueOnce("nouveau");
    const cle = jeton();
    await expect(renouvelerUneFois(cle, renouveler, reussi)).resolves.toBe("inchange");
    await expect(renouvelerUneFois(cle, renouveler, reussi)).resolves.toBe("nouveau");
    expect(renouveler).toHaveBeenCalledTimes(2);
  });

  it("réessaie après une erreur", async () => {
    const renouveler = vi.fn().mockRejectedValueOnce(new Error("panne")).mockResolvedValueOnce("nouveau");
    const cle = jeton();
    await expect(renouvelerUneFois(cle, renouveler, reussi)).rejects.toThrow("panne");
    await expect(renouvelerUneFois(cle, renouveler, reussi)).resolves.toBe("nouveau");
  });

  it("garde les sessions séparées", async () => {
    const renouveler = vi.fn().mockResolvedValue("nouveau");
    await Promise.all([renouvelerUneFois(jeton(), renouveler, reussi), renouvelerUneFois(jeton(), renouveler, reussi)]);
    expect(renouveler).toHaveBeenCalledTimes(2);
  });
});
