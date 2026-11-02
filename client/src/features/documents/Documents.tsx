"use client";

import { useState } from "react";
import { FileDown, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { messageErreurPdf } from "@/lib/documents";
import { telechargerDocument, type ObjetDocument, type TypeDocument } from "./api";
import { cn } from "@/lib/utils";
import { useTranslations } from "next-intl";

/** Download buttons for the PDFs of a paid item (voucher, receipt, invoice; receipt only for a donation). */
export default function Documents({ objet, id, className }: { objet: ObjetDocument; id: string; className?: string }) {
  const t = useTranslations("documents");
  const [enCours, setEnCours] = useState<TypeDocument | null>(null);
  const types: TypeDocument[] = objet === "don" ? ["recu"] : ["bon", "recu", "facture"];

  const nom = (doc: TypeDocument) => t(objet === "don" ? "don" : doc);

  async function telecharger(doc: TypeDocument) {
    setEnCours(doc);
    try {
      await telechargerDocument(objet, id, doc);
    } catch (err) {
      toast.error(await messageErreurPdf(err, t("erreur")));
    } finally {
      setEnCours(null);
    }
  }

  return (
    <div className={cn("flex flex-wrap items-center gap-2", className)}>
      <span className="text-xs text-gray-500">{t("titre")}</span>
      {types.map((doc) => (
        <button
          key={doc}
          type="button"
          onClick={() => telecharger(doc)}
          disabled={enCours !== null}
          aria-label={t("telecharger", { nom: nom(doc).toLowerCase() })}
          className="inline-flex items-center gap-1.5 min-h-[36px] px-3 py-1.5 rounded-full border border-gray-200 bg-white text-xs font-semibold text-dark hover:border-primary hover:text-primary transition-colors disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
        >
          {enCours === doc ? <Loader2 size={14} className="animate-spin" aria-hidden /> : <FileDown size={14} aria-hidden />}
          {nom(doc)}
        </button>
      ))}
    </div>
  );
}
