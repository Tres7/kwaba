"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { ArrowLeft, FileClock } from "lucide-react";
import { toast } from "sonner";
import { Link } from "@/i18n/navigation";
import api, { estErreurApi } from "@/lib/api";
import { telechargerPdf } from "@/lib/documents";
import LectureSignature from "@/components/contrats/LectureSignature";
import type { ContratPublic, SignatureContrat } from "@/types/api/contrat";

/** Host agreement: read and signed from the host space (the signed-in account authenticates the signer). */
export default function ContratHotePage() {
  const t = useTranslations("contrat");
  const queryClient = useQueryClient();
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["contrat-hote"],
    queryFn: async () => (await api.get<ContratPublic>("/v1/contrats/hote/")).data,
    retry: false,
  });

  const signer = async (donnees: SignatureContrat) => {
    try {
      const { data: signe } = await api.post<ContratPublic>("/v1/contrats/hote/signer/", { ...donnees, version: data?.version });
      queryClient.setQueryData(["contrat-hote"], signe);
      queryClient.invalidateQueries({ queryKey: ["verification"] });
      toast.success(t("merci"));
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      // Text changed in the meantime: the new text is loaded, to be read again
      if (estErreurApi(err) && err.response?.status === 409) {
        await refetch();
        window.scrollTo({ top: 0, behavior: "smooth" });
        throw new Error(t("versionModifiee"));
      }
      throw err;
    }
  };

  return (
    <div className="bg-light min-h-[70vh] px-4 py-8 sm:py-12">
      <div className="max-w-3xl mx-auto">
        <Link href="/hote/espace" className="inline-flex items-center gap-1.5 text-sm font-semibold text-primary mb-6 hover:underline">
          <ArrowLeft size={16} aria-hidden /> {t("retourEspace")}
        </Link>
        {isLoading ? (
          <div className="h-96 skeleton rounded-3xl" aria-busy="true" />
        ) : isError || !data ? (
          <div className="bg-white rounded-3xl border border-gray-100 p-8 text-center">
            <FileClock size={40} className="mx-auto text-gray-400" aria-hidden />
            <p className="mt-4 text-dark font-semibold">
              {estErreurApi(error) && error.response?.status === 403 ? t("reserveHotes") : t("indisponible")}
            </p>
          </div>
        ) : (
          <LectureSignature contrat={data} onSigner={signer} onTelecharger={() => telechargerPdf("/v1/contrats/hote/pdf/", "contrat-hote.pdf")} />
        )}
      </div>
    </div>
  );
}
