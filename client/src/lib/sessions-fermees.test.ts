import { afterEach, describe, expect, it, vi } from "vitest";
import { fermerSession, sessionFermee } from "./sessions-fermees";

describe("sessions fermées", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("reconnaît la session fermée, pas les autres", () => {
    fermerSession("jeton-a", 1000);
    expect(sessionFermee("jeton-a")).toBe(true);
    expect(sessionFermee("jeton-b")).toBe(false);
  });

  it("ne bloque pas une session sans jeton", () => {
    expect(sessionFermee(undefined)).toBe(false);
  });

  it("oublie la session une fois le cookie expiré", () => {
    vi.useFakeTimers();
    fermerSession("jeton-c", 1000);
    vi.advanceTimersByTime(999);
    expect(sessionFermee("jeton-c")).toBe(true);
    vi.advanceTimersByTime(1);
    expect(sessionFermee("jeton-c")).toBe(false);
  });
});
