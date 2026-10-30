/** Base of the relative addresses: only the scheme of the result matters here. */
const BASE = "https://kwa-ba.invalid";

// The hosted pages change with the provider's environment (sandbox-process.fedapay.com, www.sandbox.paypal.com)
const DOMAINES_PAIEMENT = ["fedapay.com", "paypal.com"];

/** Address from the API for an href: http(s) or relative, otherwise nothing (a javascript: link would run on click). */
export function urlExterneSure(url: string | null | undefined): string | undefined {
  if (!url) return undefined;
  try {
    const { protocol } = new URL(url, BASE);
    return protocol === "https:" || protocol === "http:" ? url : undefined;
  } catch {
    return undefined;
  }
}

/** Hosted page of a payment provider, the only place where the API can send the traveller. */
export function estPagePaiement(url: string): boolean {
  try {
    const { protocol, hostname } = new URL(url);
    return protocol === "https:" && DOMAINES_PAIEMENT.some((d) => hostname === d || hostname.endsWith(`.${d}`));
  } catch {
    return false;
  }
}
