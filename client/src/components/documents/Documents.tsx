"use client";

import { useState } from "react";
import { FileDown, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { messageErreurPdf, telechargerDocument, type ObjetDocument, type TypeDocument } from "@/lib/documents";
import { cn } from "@/lib/utils";
import { useFormat } from "@/lib/format";

const NOMS: Record<TypeDocument, { fr: string; en: string }> = {
  bon: { fr: "Bon", en: "Voucher" },
  recu: { fr: "Reçu", en: "Receipt" },
  facture: { fr: "Facture", en: "Invoice" },
};

/** Download buttons for the PDFs of a paid item (voucher, receipt, invoice; receipt only for a donation). */
export default function Documents({ objet, id, className }: { objet: ObjetDocument; id: string; className?: string }) {
  const { selon } = useFormat();
  const [enCours, setEnCours] = useState<TypeDocument | null>(null);
  const types: TypeDocument[] = objet === "don" ? ["recu"] : ["bon", "recu", "facture"];

  async function telecharger(doc: TypeDocument) {
    setEnCours(doc);
    try {
      await telechargerDocument(objet, id, doc);
    } catch (err) {
      toast.error(await messageErreurPdf(err, selon({ fr: "Le document n'a pas pu être téléchargé.", en: "The document could not be downloaded." })));
    } finally {
      setEnCours(null);
    }
  }

  return (
    <div className={cn("flex flex-wrap items-center gap-2", className)}>
      <span className="text-xs text-gray-500">{selon({ fr: "Documents :", en: "Documents:" })}</span>
      {types.map((doc) => (
        <button
          key={doc}
          type="button"
          onClick={() => telecharger(doc)}
          disabled={enCours !== null}
          aria-label={selon({ fr: `Télécharger : ${objet === "don" ? "reçu de don" : NOMS[doc].fr.toLowerCase()} (PDF)`, en: `Download ${objet === "don" ? "donation receipt" : NOMS[doc].en.toLowerCase()} (PDF)` })}
          className="inline-flex items-center gap-1.5 min-h-[36px] px-3 py-1.5 rounded-full border border-gray-200 bg-white text-xs font-semibold text-dark hover:border-primary hover:text-primary transition-colors disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
        >
          {enCours === doc ? <Loader2 size={14} className="animate-spin" aria-hidden /> : <FileDown size={14} aria-hidden />}
          {objet === "don" ? selon({ fr: "Reçu de don", en: "Donation receipt" }) : selon(NOMS[doc])}
        </button>
      ))}
    </div>
  );
}
