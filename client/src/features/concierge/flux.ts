/** Reads an SSE stream ("event: … / data: …" events) and calls `surEvenement` for each one. */
export async function lireFlux(reponse: Response, surEvenement: (nom: string, donnees: Record<string, unknown>) => void) {
  const lecteur = reponse.body!.getReader();
  const decodeur = new TextDecoder();
  let tampon = "";
  for (;;) {
    const { done, value } = await lecteur.read();
    if (done) break;
    tampon += decodeur.decode(value, { stream: true });
    let fin;
    while ((fin = tampon.indexOf("\n\n")) >= 0) {
      const bloc = tampon.slice(0, fin);
      tampon = tampon.slice(fin + 2);
      const nom = bloc.match(/^event: (.+)$/m)?.[1];
      const data = bloc.match(/^data: (.+)$/m)?.[1];
      if (nom && data) surEvenement(nom, JSON.parse(data));
    }
  }
}
