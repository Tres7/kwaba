import { beforeEach, describe, expect, it, vi } from "vitest";
import api, { SANS_REJET } from "@/lib/api";
import { confirmerReinitialisation, demanderReinitialisation, inscrire, lireCleCaptcha, renvoyerCode } from "./api";

vi.mock("@/lib/api", () => ({ default: { get: vi.fn(), post: vi.fn() }, SANS_REJET: { validateStatus: () => true } }));

describe("auth", () => {
  beforeEach(() => vi.clearAllMocks());

  it("les formulaires lisent eux-mêmes les erreurs de l'API", async () => {
    await inscrire({ email: "a@b.c" });
    expect(api.post).toHaveBeenLastCalledWith("/v1/auth/register/", { email: "a@b.c" }, SANS_REJET);
    await renvoyerCode("a@b.c");
    expect(api.post).toHaveBeenLastCalledWith("/v1/auth/resend-code/", { email: "a@b.c" }, SANS_REJET);
    await demanderReinitialisation("a@b.c");
    expect(api.post).toHaveBeenLastCalledWith("/v1/auth/password-reset/", { email: "a@b.c" }, SANS_REJET);
    const corps = { email: "a@b.c", code: "123456", password: "x", password_confirm: "x" };
    await confirmerReinitialisation(corps);
    expect(api.post).toHaveBeenLastCalledWith("/v1/auth/password-reset/confirm/", corps, SANS_REJET);
  });

  it("lit la clé du captcha", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: { site_key: "cle" } });
    await expect(lireCleCaptcha()).resolves.toBe("cle");
    expect(api.get).toHaveBeenCalledWith("/v1/auth/captcha/");
  });
});
