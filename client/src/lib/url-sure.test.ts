import { describe, expect, it } from "vitest";
import { estPagePaiement, urlExterneSure } from "./url-sure";

describe("urlExterneSure", () => {
  it.each([
    "https://ong.example/a-propos",
    "http://ong.example",
    "https://kwa-ba.com/media/give/preuve.pdf",
    "/media/give/preuve.pdf",
  ])("garde %s", (url) => {
    expect(urlExterneSure(url)).toBe(url);
  });

  it.each([
    "javascript:alert(1)",
    "JavaScript:alert(1)",
    " javascript:alert(1)",
    "java\tscript:alert(1)",
    "data:text/html,<script>alert(1)</script>",
    "vbscript:msgbox(1)",
    "file:///etc/passwd",
    "ftp://ong.example/x",
  ])("écarte %j", (url) => {
    expect(urlExterneSure(url)).toBeUndefined();
  });

  it.each([[null], [undefined], [""]])("rien pour %j", (url) => {
    expect(urlExterneSure(url)).toBeUndefined();
  });
});

describe("estPagePaiement", () => {
  it.each([
    "https://process.fedapay.com/abc",
    "https://sandbox-process.fedapay.com/abc",
    "https://www.paypal.com/checkoutnow?token=ORDER1",
    "https://www.sandbox.paypal.com/checkoutnow?token=ORDER1",
  ])("accepte %s", (url) => {
    expect(estPagePaiement(url)).toBe(true);
  });

  it.each([
    "http://process.fedapay.com/abc",
    "https://fedapay.com.evil.example/abc",
    "https://evilfedapay.com/abc",
    "https://paypal.com@evil.example/abc",
    "https://evil.example/https://www.paypal.com/",
    "https://www.paypal.com.evil.example/",
    "javascript:alert(1)",
    "/reservation/1",
    "",
  ])("refuse %j", (url) => {
    expect(estPagePaiement(url)).toBe(false);
  });
});
