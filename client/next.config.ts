import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";
import { politiqueCsp, RAPPORTS_CSP } from "./src/lib/csp";

// HSTS, X-Content-Type-Options and Referrer-Policy are set by nginx for the whole site (deploy/vps/nginx):
// repeating them here would send them twice.
const securityHeaders = [
  { key: "Reporting-Endpoints", value: `csp="${RAPPORTS_CSP}"` },
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
      // Pages get their CSP from middleware.ts, with a nonce for each response. Never here for every path: the browser
      // would enforce both policies, and this one blocks the scripts of the pages.
      { source: "/api/:path*", headers: [{ key: "Content-Security-Policy", value: politiqueCsp() }] },
      // Home page photos kept a week by the browser (Next.js serves public/ with max-age=0).
      // To change a photo, give it a new name: otherwise the old one would stay in the cache.
      { source: "/accueil/:fichier*", headers: [{ key: "Cache-Control", value: "public, max-age=604800, stale-while-revalidate=86400" }] },
    ];
  },
};

export default createNextIntlPlugin("./src/i18n/request.ts")(nextConfig);
