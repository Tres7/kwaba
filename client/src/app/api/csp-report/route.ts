import { NextResponse, type NextRequest } from "next/server";
import { lireRapportsCsp } from "@/lib/rapport-csp";

export const dynamic = "force-dynamic";

// nginx already limits the size and the rate per address. Anyone can post here: the logs stay capped for the whole
// process, and a report is a lead to check, never a proof.
const LIMITE_PAR_MINUTE = 60;
const TAILLE_MAX = 16_384;

let journal = { minute: 0, lignes: 0 };

export async function POST(req: NextRequest) {
  const corps = await req.text();
  if (corps.length > TAILLE_MAX) return new NextResponse(null, { status: 413 });

  let contenu: unknown;
  try {
    contenu = JSON.parse(corps);
  } catch {
    return new NextResponse(null, { status: 204 });
  }

  const minute = Math.floor(Date.now() / 60_000);
  if (minute !== journal.minute) journal = { minute, lignes: 0 };
  for (const violation of lireRapportsCsp(contenu)) {
    if (journal.lignes >= LIMITE_PAR_MINUTE) break;
    journal.lignes += 1;
    // JSON.stringify: a line break in a report cannot forge a log line
    console.warn(`csp-violation ${JSON.stringify(violation)}`);
  }
  return new NextResponse(null, { status: 204 });
}
