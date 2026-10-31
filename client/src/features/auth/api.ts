import api, { SANS_REJET } from "@/lib/api";

const AUTH = "/v1/auth";

/** These answers are read by the forms, errors included: they do not reject (SANS_REJET). */
export function inscrire(compte: Record<string, unknown>) {
  return api.post(`${AUTH}/register/`, compte, SANS_REJET);
}

export function renvoyerCode(email: string) {
  return api.post(`${AUTH}/resend-code/`, { email }, SANS_REJET);
}

export function demanderReinitialisation(email: string) {
  return api.post(`${AUTH}/password-reset/`, { email }, SANS_REJET);
}

export function confirmerReinitialisation(reinitialisation: { email: string; code: string; password: string; password_confirm: string }) {
  return api.post(`${AUTH}/password-reset/confirm/`, reinitialisation, SANS_REJET);
}

export async function lireCleCaptcha() {
  return (await api.get<{ site_key: string }>(`${AUTH}/captcha/`)).data.site_key;
}
