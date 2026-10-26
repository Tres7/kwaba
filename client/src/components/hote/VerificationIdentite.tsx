"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { CheckCircle2, ShieldCheck, Upload } from "lucide-react";
import { toast } from "sonner";
import api, { apiErrorMessage } from "@/lib/api";
import Select from "@/components/ui/Select";
import { cn } from "@/lib/utils";

type TypePiece = "cni" | "passeport" | "permis" | "sejour";
const TYPES: TypePiece[] = ["cni", "passeport", "permis", "sejour"];

interface PieceIdentite {
  statut: "absente" | "soumise" | "verifiee" | "refusee";
  type_piece?: TypePiece;
  motif_refus?: string;
}

/** The host's identity document, checked by the field agent during the visit of the listing. */
export default function VerificationIdentite() {
  const t = useTranslations("espaceHote.verification");
  const queryClient = useQueryClient();
  const [typePiece, setTypePiece] = useState<TypePiece>("cni");
  const [fichier, setFichier] = useState<File | null>(null);
  const [envoi, setEnvoi] = useState(false);

  const { data: piece, isLoading } = useQuery({
    queryKey: ["verification", "identite"],
    queryFn: async () => (await api.get<PieceIdentite>("/v1/verifications/identite/")).data,
  });

  if (isLoading || !piece) return null;

  if (piece.statut === "verifiee") {
    return (
      <p className="flex items-center gap-2 text-sm font-semibold text-green-700 bg-green-50 rounded-2xl px-4 py-3 mb-6">
        <CheckCircle2 size={18} /> {t("identiteVerifiee")}
      </p>
    );
  }

  const envoyer = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!fichier) {
      toast.error(t("choisirFichier"));
      return;
    }
    setEnvoi(true);
    const donnees = new FormData();
    donnees.append("type_piece", typePiece);
    donnees.append("fichier", fichier);
    try {
      await api.post("/v1/verifications/identite/", donnees, { headers: { "Content-Type": "multipart/form-data" } });
      toast.success(t("envoyee"));
      setFichier(null);
      await queryClient.invalidateQueries({ queryKey: ["verification", "identite"] });
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setEnvoi(false);
    }
  };

  const soumise = piece.statut === "soumise";
  return (
    <section className={cn("rounded-3xl border p-5 sm:p-6 mb-6", soumise ? "bg-white border-gray-100" : "bg-amber-50 border-amber-200")}>
      <h2 className="flex items-center gap-2 font-heading font-bold text-dark"><ShieldCheck size={20} className="text-primary" /> {t("identiteTitre")}</h2>
      {soumise ? (
        <p className="text-sm text-gray-600 mt-2">{t("identiteSoumise")}</p>
      ) : (
        <p className="text-sm text-gray-700 mt-2">{t("identiteAide")}</p>
      )}
      {piece.statut === "refusee" && piece.motif_refus && (
        <p role="alert" className="text-sm text-red-700 bg-red-50 rounded-xl px-3 py-2 mt-3">{t("identiteRefusee", { motif: piece.motif_refus })}</p>
      )}

      <form method="post" onSubmit={envoyer} className="mt-4 grid grid-cols-1 sm:grid-cols-[220px_1fr_auto] gap-3 sm:items-end">
        <div>
          <p className="block text-xs font-bold text-dark uppercase tracking-wide mb-2">{t("typePiece")}</p>
          <Select label={t("typePiece")} value={typePiece} onChange={setTypePiece} options={TYPES.map((id) => ({ value: id, label: t(`types.${id}`) }))} />
        </div>
        <label className="block">
          <span className="block text-xs font-bold text-dark uppercase tracking-wide mb-2">{t("fichier")}</span>
          <input
            type="file" accept="image/jpeg,image/png,image/webp,application/pdf"
            onChange={(e) => setFichier(e.target.files?.[0] ?? null)}
            className="block w-full text-sm text-gray-600 file:mr-3 file:px-4 file:py-2.5 file:rounded-xl file:border-0 file:bg-gray-100 file:text-dark file:font-semibold hover:file:bg-gray-200"
          />
        </label>
        <button type="submit" disabled={envoi} className="flex items-center justify-center gap-2 bg-primary text-white font-bold px-5 py-3 rounded-xl disabled:opacity-60">
          <Upload size={16} /> {envoi ? t("envoi") : soumise ? t("remplacer") : t("envoyer")}
        </button>
      </form>
      <p className="text-xs text-gray-500 mt-3">{t("confidentialite")}</p>
    </section>
  );
}
