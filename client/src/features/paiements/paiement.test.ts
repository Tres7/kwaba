import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import api from "@/lib/api";
import { allerPayer, enEuros, minutesRestantes, payerLocation, payerTransfert, versPagePaiement } from "./paiement";

vi.mock("@/lib/api", () => ({ default: { post: vi.fn() } }));

const assign = vi.fn();

describe("départ vers la page de paiement", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubGlobal("window", { location: { assign } });
  });
  afterEach(() => vi.unstubAllGlobals());

  it("refuse une adresse qui n'est pas celle d'un prestataire", () => {
    expect(() => versPagePaiement("https://evil.example/pay")).toThrow("Adresse de paiement inattendue");
    expect(assign).not.toHaveBeenCalled();
  });

  it.each([
    [allerPayer, "/v1/paiements/reservations/r1/payer/"],
    [payerTransfert, "/v1/transferts/r1/payer/"],
    [payerLocation, "/v1/locations/r1/payer/"],
  ])("une adresse inattendue de l'API ne quitte pas le site (%#)", async (payer, chemin) => {
    vi.mocked(api.post).mockResolvedValue({ data: { url: "https://evil.example/pay" } });
    await expect((payer as (id: string, moyen: never) => Promise<void>)("r1", "carte" as never)).rejects.toThrow();
    expect(api.post).toHaveBeenCalledWith(chemin, { moyen: "carte" });
    expect(assign).not.toHaveBeenCalled();
  });
});

describe("minutesRestantes", () => {
  it("arrondit à la minute supérieure et ne descend pas sous zéro", () => {
    vi.useFakeTimers({ now: new Date("2026-12-01T10:00:00Z") });
    expect(minutesRestantes("2026-12-01T10:00:30Z")).toBe(1);
    expect(minutesRestantes("2026-12-01T09:00:00Z")).toBe(0);
    expect(minutesRestantes(null)).toBeNull();
    vi.useRealTimers();
  });
});

describe("enEuros", () => {
  it("convertit à la parité fixe", () => {
    expect(enEuros(655957, 655.957)).toMatch(/^1\s?000,00\s€$/);
  });
});
