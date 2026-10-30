import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const isDev = process.env.NODE_ENV !== "production";

/** Origin of the API called by the browser (baked at build time, like NEXT_PUBLIC_API_URL). */
function apiOrigin(): string {
  try {
    return new URL(process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api").origin;
  } catch {
    return "";
  }
}

// Content security policy: the browser only loads what comes from these origins. Limits the impact
// of an XSS flaw (no script injected from another site, no data sent to an unknown server).
// 'unsafe-inline' is still needed by the Next.js hydration scripts without a nonce.
const csp = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline' https://accounts.google.com/gsi/client https://challenges.cloudflare.com${isDev ? " 'unsafe-eval'" : ""}`,
  "style-src 'self' 'unsafe-inline' https://accounts.google.com/gsi/style",
  // Photos: site and API (R2 storage is served under /photos/), Google avatars, Unsplash (backgrounds in the code and
  // seeded experiences). Same hosts as IMAGES_HOTES_AUTORISES on the API. Never "https:": a script could send data to
  // any site through the address of an image.
  `img-src 'self' data: blob: ${apiOrigin()} https://*.googleusercontent.com https://images.unsplash.com${isDev ? " http: https:" : ""}`,
  "font-src 'self' data:",
  `connect-src 'self' ${apiOrigin()} https://accounts.google.com${isDev ? " ws: http://localhost:8000" : ""}`,
  "frame-src https://accounts.google.com https://maps.google.com https://www.google.com https://challenges.cloudflare.com",
  "frame-ancestors 'none'",
  "object-src 'none'",
  "base-uri 'self'",
  // Payments (FedaPay, PayPal) go through redirects, not forms: only the site itself receives
  "form-action 'self'",
  ...(isDev ? [] : ["upgrade-insecure-requests"]),
].join("; ");

// HSTS, X-Content-Type-Options and Referrer-Policy are set by nginx for the whole site (deploy/vps/nginx):
// repeating them here would send them twice.
const securityHeaders = [
  { key: "Content-Security-Policy", value: csp },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=(), usb=()" },
  // The Google Identity Services window must be able to talk to the page (sign-in popup)
  { key: "Cross-Origin-Opener-Policy", value: "same-origin-allow-popups" },
];

const nextConfig: NextConfig = {
  output: "standalone",
  // No "X-Powered-By: Next.js" header nor public source maps in production
  poweredByHeader: false,
  productionBrowserSourceMaps: false,
  // Only bundles the Phosphor icons actually imported
  experimental: { optimizePackageImports: ["@phosphor-icons/react"] },
  async headers() {
    return [
      { source: "/:path*", headers: securityHeaders },
      // Home page photos kept a week by the browser (Next.js serves public/ with max-age=0).
      // To change a photo, give it a new name: otherwise the old one would stay in the cache.
      { source: "/accueil/:fichier*", headers: [{ key: "Cache-Control", value: "public, max-age=604800, stale-while-revalidate=86400" }] },
    ];
  },
};

export default createNextIntlPlugin("./src/i18n/request.ts")(nextConfig);
