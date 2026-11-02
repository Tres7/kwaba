import { describe, expect, it } from "vitest";
import { lireFlux } from "./flux";

function reponse(...morceaux: string[]) {
  const encodeur = new TextEncoder();
  const corps = new ReadableStream<Uint8Array>({
    start(controleur) {
      morceaux.forEach((m) => controleur.enqueue(encodeur.encode(m)));
      controleur.close();
    },
  });
  return new Response(corps);
}

async function evenements(...morceaux: string[]) {
  const recus: [string, Record<string, unknown>][] = [];
  await lireFlux(reponse(...morceaux), (nom, donnees) => recus.push([nom, donnees]));
  return recus;
}

describe("lireFlux", () => {
  it("rend chaque événement du flux", async () => {
    await expect(evenements('event: texte\ndata: {"delta":"Bon"}\n\nevent: fin\ndata: {}\n\n')).resolves.toEqual([
      ["texte", { delta: "Bon" }], ["fin", {}],
    ]);
  });

  it("recolle un événement coupé en deux morceaux", async () => {
    await expect(evenements('event: texte\nda', 'ta: {"delta":"jour"}\n\n')).resolves.toEqual([["texte", { delta: "jour" }]]);
  });

  it("recolle un caractère accentué coupé entre deux morceaux", async () => {
    const octets = new TextEncoder().encode('event: texte\ndata: {"delta":"é"}\n\n');
    const coupe = octets.indexOf(0xc3) + 1;
    const corps = new ReadableStream<Uint8Array>({
      start(c) {
        c.enqueue(octets.slice(0, coupe));
        c.enqueue(octets.slice(coupe));
        c.close();
      },
    });
    const recus: unknown[] = [];
    await lireFlux(new Response(corps), (_, d) => recus.push(d));
    expect(recus).toEqual([{ delta: "é" }]);
  });
});
