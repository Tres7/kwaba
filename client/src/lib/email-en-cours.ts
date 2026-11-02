const CLE = "verify_email";

/**
 * Address being confirmed, kept between the sign-up, code and sign-in pages of the tab. Never in the URL: it would end up
 * in the server logs and the browser history. Storage unavailable: the code page asks for the address.
 */
export function retenirEmail(email: string) {
  try {
    sessionStorage.setItem(CLE, email);
  } catch { /* see above */ }
}

export function emailRetenu(): string {
  try {
    return sessionStorage.getItem(CLE) ?? "";
  } catch {
    return "";
  }
}

export function oublierEmail() {
  try {
    sessionStorage.removeItem(CLE);
  } catch { /* see above */ }
}
