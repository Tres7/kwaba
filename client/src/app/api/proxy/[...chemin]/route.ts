import type { NextRequest } from "next/server";
import { getToken } from "next-auth/jwt";
import { getApiBaseUrl } from "@/lib/api-url";
import { cheminApi, entetesVersApi, entetesVersNavigateur, origineAutorisee } from "@/lib/proxy";

export const dynamic = "force-dynamic";

const secureCookie = (process.env.AUTH_URL ?? "").startsWith("https://");
const API_PUBLIQUE = new URL(process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api");

/**
 * Relays the browser's API calls and adds the session's token, which therefore never reaches the browser's JavaScript.
 * The cookie is only read here: renewing the token stays with /api/auth/session, the only place that can save the new
 * tokens. An expired token gets a 401 from the API, and lib/api.ts renews it there before replaying the request.
 */
async function relayer(req: NextRequest, { params }: { params: Promise<{ chemin: string[] }> }) {
  const chemin = cheminApi((await params).chemin);
  if (!chemin) return new Response(null, { status: 404 });

  const hote = req.headers.get("x-forwarded-host") ?? req.headers.get("host");
  if (!origineAutorisee(req.method, req.headers.get("origin"), hote)) {
    return Response.json({ detail: "Origine non autorisée." }, { status: 403 });
  }

  const session = await getToken({ req, secret: process.env.AUTH_SECRET, secureCookie });
  const accessToken = session && !session.error ? session.accessToken : undefined;

  let reponse: Response;
  try {
    reponse = await fetch(`${getApiBaseUrl()}/${chemin}${req.nextUrl.search}`, {
      method: req.method,
      headers: entetesVersApi(req.headers, accessToken, API_PUBLIQUE),
      // Streamed, not read into memory (photos, identity documents). Django needs the Content-Length, which is kept.
      body: req.body,
      duplex: "half",
      redirect: "manual",
      cache: "no-store",
      signal: req.signal,
    } as RequestInit);
  } catch (erreur) {
    // A visitor who left is not a failure. The first two segments only: the rest may be a personal link (contract signature)
    if (!req.signal.aborted) {
      const cause = (erreur as { cause?: { code?: string } }).cause?.code ?? String(erreur);
      console.error("proxy-echec", JSON.stringify({ module: chemin.split("/").slice(0, 2).join("/"), cause }));
    }
    return Response.json({ detail: "Service momentanément indisponible." }, { status: 502 });
  }
  return new Response(reponse.body, { status: reponse.status, headers: entetesVersNavigateur(reponse.headers) });
}

export { relayer as DELETE, relayer as GET, relayer as HEAD, relayer as PATCH, relayer as POST, relayer as PUT };
