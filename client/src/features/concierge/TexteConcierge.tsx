import { Fragment, type ReactNode } from "react";

/** Light formatting of the Concierge's answers (titles, lists, **bold**, separators), without injected HTML. */
function enLigne(texte: string) {
  return texte.split(/(\*\*[^*]+\*\*|\*[^*\s][^*]*\*)/g).map((morceau, i) => {
    if (morceau.startsWith("**") && morceau.endsWith("**") && morceau.length > 4) {
      return <strong key={i} className="font-semibold">{morceau.slice(2, -2)}</strong>;
    }
    if (morceau.startsWith("*") && morceau.endsWith("*") && morceau.length > 2) {
      return <em key={i}>{morceau.slice(1, -1)}</em>;
    }
    return <Fragment key={i}>{morceau}</Fragment>;
  });
}

const PUCE = /^\s*([-*•])\s+/;
const NUMERO = /^\s*\d+[.)]\s+/;

export default function TexteConcierge({ texte }: { texte: string }) {
  const elements: ReactNode[] = [];
  let paragraphe: string[] = [];
  let liste: { numerotee: boolean; items: string[] } | null = null;

  const fermerParagraphe = () => {
    if (paragraphe.length) {
      const lignes = paragraphe;
      elements.push(<p key={elements.length}>{lignes.map((l, j) => <Fragment key={j}>{j > 0 && <br />}{enLigne(l)}</Fragment>)}</p>);
      paragraphe = [];
    }
  };
  const fermerListe = () => {
    if (liste) {
      const { numerotee, items } = liste;
      const Balise = numerotee ? "ol" : "ul";
      elements.push(
        <Balise key={elements.length} className={numerotee ? "list-decimal pl-5 space-y-1" : "list-disc pl-5 space-y-1"}>
          {items.map((it, j) => <li key={j}>{enLigne(it)}</li>)}
        </Balise>,
      );
      liste = null;
    }
  };

  for (const brute of texte.replace(/\r/g, "").split("\n")) {
    const ligne = brute.trimEnd();
    if (!ligne.trim()) {
      fermerParagraphe();
      fermerListe();
    } else if (/^\s*(-{3,}|\*{3,}|_{3,})\s*$/.test(ligne)) {
      fermerParagraphe();
      fermerListe();
      elements.push(<hr key={elements.length} className="border-gray-200" />);
    } else if (/^#{1,6}\s+/.test(ligne)) {
      fermerParagraphe();
      fermerListe();
      elements.push(<p key={elements.length} className="font-heading font-bold text-[15px] pt-1">{enLigne(ligne.replace(/^#{1,6}\s+/, "").replace(/\*\*/g, ""))}</p>);
    } else if (PUCE.test(ligne) || NUMERO.test(ligne)) {
      fermerParagraphe();
      const numerotee = NUMERO.test(ligne);
      if (!liste || liste.numerotee !== numerotee) {
        fermerListe();
        liste = { numerotee, items: [] };
      }
      liste.items.push(ligne.replace(numerotee ? NUMERO : PUCE, ""));
    } else {
      fermerListe();
      paragraphe.push(ligne.trim());
    }
  }
  fermerParagraphe();
  fermerListe();

  return <div className="space-y-2.5 leading-relaxed">{elements}</div>;
}
