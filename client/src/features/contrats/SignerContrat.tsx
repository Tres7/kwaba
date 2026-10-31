"use client";

import { useParams } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { FileX2 } from "lucide-react";
import { toast } from "sonner";
import { lireContrat, signerContrat, telechargerContrat } from "./api";
import LectureSignature from "./LectureSignature";
import type { SignatureContrat } from "./types";

export default function ContratPage() {
  const { jeton } = useParams<{ jeton: string }>();
  const t = useTranslations("contrat");
  const queryClient = useQueryClient();
  const cle = ["contrat", jeton];
  const { data, isLoading, isError } = useQuery({
    queryKey: cle,
    queryFn: () => lireContrat(jeton),
    retry: false,
  });

  const signer = async (donnees: SignatureContrat) => {
    queryClient.setQueryData(cle, await signerContrat(jeton, donnees));
    toast.success(t("merci"));
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <div className="bg-light min-h-[70vh] px-4 py-8 sm:py-12">
      <div className="max-w-3xl mx-auto">
        {isLoading ? (
          <div className="space-y-4" aria-busy="true">
            <div className="h-10 w-2/3 skeleton rounded-xl" />
            <div className="h-96 skeleton rounded-3xl" />
          </div>
        ) : isError || !data ? (
          <div className="bg-white rounded-3xl border border-gray-100 p-8 text-center">
            <FileX2 size={40} className="mx-auto text-gray-400" aria-hidden />
            <p className="mt-4 text-dark font-semibold">{t("introuvable")}</p>
          </div>
        ) : (
          <LectureSignature contrat={data} onSigner={signer}
            onTelecharger={() => telechargerContrat(jeton, data.reference)} />
        )}
      </div>
    </div>
  );
}
