import { NextResponse, type NextRequest } from "next/server";
import { getToken } from "next-auth/jwt";
import createIntlMiddleware from "next-intl/middleware";
import { routing } from "@/i18n/routing";
import { moduleDuChemin, type ReglagesSite } from "@/lib/modules";

// Pages reserved for signed-in users (the help centre stays public)
const PROTECTED = ["/profil", "/favoris", "/messages", "/reservation", "/hote/espace", "/backoffice", "/agent", "/give/don"];
const PUBLIC_EXCEPTIONS = ["/profil/aide"];
// Public landing pages; their sub-pages (transfer tracking, group trip, invitation) require signing in
const PROTECTED_SUBPATHS = ["/transfert", "/together", "/location"];
// Authentication pages useless once signed in
const GUEST_ONLY = ["/login", "/register"];
// Internal spaces served outside the language routes (app/backoffice, app/agent)
const SANS_LANGUE = ["/backoffice", "/agent"];

// Language: /en prefix, otherwise NEXT_LOCALE cookie, otherwise browser language (first visit)
const intl = createIntlMiddleware(routing);

/** Path without the language prefix (/en/profil → /profil) and prefix to put back in redirects. */
function sansLangue(pathname: string) {
  const langue = routing.locales.find((l) => l !== routing.defaultLocale && (pathname === `/${l}` || pathname.startsWith(`/${l}/`)));
  if (!langue) return { chemin: pathname, prefixe: "" };
  return { chemin: pathname.slice(langue.length + 1) || "/", prefixe: `/${langue}` };
}

// Session read directly from the cookie, without the auth() wrapper: with AUTH_URL (required in production
// behind nginx), this wrapper rewrites the request origin and Next.js then treats the next-intl language
// rewrite as an external proxy (500 error in standalone mode). Token renewal is still done by the Auth.js
// routes and the server components.
const secureCookie = (process.env.AUTH_URL ?? "").startsWith("https://");

// Displayed modules, read again from the API at most every minute. API unreachable: every module is considered
// hidden (launch state), so as never to show a page that should be hidden.
const DUREE_MODULES_MS = 60_000;
let modulesEnCache: { valeur: ReglagesSite["modules"] | null; lu: number } = { valeur: null, lu: 0 };

async function modulesAffiches(): Promise<ReglagesSite["modules"] | null> {
  if (Date.now() - modulesEnCache.lu < DUREE_MODULES_MS) return modulesEnCache.valeur;
  const base = process.env.INTERNAL_API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
  let valeur: ReglagesSite["modules"] | null = null;
  try {
    const res = await fetch(`${base}/v1/site/`, { cache: "no-store", signal: AbortSignal.timeout(3000) });
    if (res.ok) valeur = ((await res.json()) as ReglagesSite).modules;
  } catch {
    valeur = null;
  }
  modulesEnCache = { valeur, lu: Date.now() };
  return valeur;
}

export default async function middleware(req: NextRequest) {
  const { pathname, search } = req.nextUrl;
  const token = await getToken({ req, secret: process.env.AUTH_SECRET, secureCookie });
  const isLoggedIn = !!token && !token.error;
  const { chemin, prefixe } = sansLangue(pathname);

  // Back-office and agent space only exist in French, without prefix: /en/agent (after signing in
  // on the English site, for example) has no page and would make the rendering fail. Redirect to /agent.
  if (prefixe && SANS_LANGUE.some((p) => chemin === p || chemin.startsWith(`${p}/`))) {
    return NextResponse.redirect(new URL(chemin + search, req.nextUrl.origin));
  }

  // Hidden module (Experiences, Group travel, Give, Concierge): its address redirects to the home page
  const moduleDeLaPage = moduleDuChemin(chemin);
  if (moduleDeLaPage && !(await modulesAffiches())?.[moduleDeLaPage]) {
    return NextResponse.redirect(new URL(prefixe || "/", req.nextUrl.origin));
  }

  const isProtected =
    (PROTECTED.some((p) => chemin === p || chemin.startsWith(`${p}/`)) ||
      PROTECTED_SUBPATHS.some((p) => chemin.startsWith(`${p}/`))) &&
    !PUBLIC_EXCEPTIONS.some((p) => chemin.startsWith(p));

  if (!isLoggedIn && isProtected) {
    const url = new URL(`${prefixe}/login`, req.nextUrl.origin);
    url.searchParams.set("callbackUrl", chemin + search);
    return NextResponse.redirect(url);
  }

  // Back-office: administrators only (the API also checks the role), in French
  if (chemin.startsWith("/backoffice")) {
    if (isLoggedIn && token?.role !== "admin") {
      return NextResponse.redirect(new URL(prefixe || "/", req.nextUrl.origin));
    }
    return NextResponse.next();
  }

  // Field agents' space (listing verification), in French. Display comfort only:
  // the API checks the role in the database at every request.
  if (chemin.startsWith("/agent")) {
    if (isLoggedIn && token?.role !== "agent" && token?.role !== "admin") {
      return NextResponse.redirect(new URL(prefixe || "/", req.nextUrl.origin));
    }
    return NextResponse.next();
  }

  if (isLoggedIn && GUEST_ONLY.includes(chemin)) {
    return NextResponse.redirect(new URL(prefixe || "/", req.nextUrl.origin));
  }

  return intl(req);
}

export const config = {
  // All pages, except the API, Next.js internal files and static files
  matcher: ["/((?!api|_next|_vercel|.*\\..*).*)"],
};
