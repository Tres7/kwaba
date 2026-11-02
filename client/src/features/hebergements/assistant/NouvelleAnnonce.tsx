"use client";

import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { Link, useRouter } from "@/i18n/navigation";
import { apiErrorMessage, estErreurApi } from "@/lib/api";
import { creerBrouillon } from "../api";

const DEPART = { max_guests: 2, chambres: 1, salles_de_bain: 1, lits_doubles: 1 };

/** New listing: its draft exists from the first screen, so that nothing typed is ever lost. */
export default function NouvelleAnnonce() {
  const t = useTranslations("assistantHote");
  const router = useRouter();
  const [erreur, setErreur] = useState("");
  const lance = useRef(false);

  useEffect(() => {
    if (lance.current) return;
    lance.current = true;
    creerBrouillon(DEPART)
      .then((brouillon) => router.replace(`/hote/annonce/${brouillon.id}`))
      .catch((err) => {
        // Not a candidate yet: the page that opens a candidature comes first
        if (estErreurApi(err) && err.response?.status === 403) router.replace("/hote");
        else setErreur(apiErrorMessage(err));
      });
  }, [router]);

  return (
    <div className="min-h-dvh bg-light-muted flex flex-col items-center justify-center gap-4 px-6 text-center">
      <img src="/hote/bienvenue.webp" alt="" width={800} height={800} className="assistant-flotte w-56 h-56 object-contain mix-blend-multiply" />
      {erreur ? (
        <>
          <p role="alert" className="text-dark font-semibold max-w-sm">{erreur}</p>
          <Link href="/hote/espace" className="font-bold text-primary underline">{t("retourEspace")}</Link>
        </>
      ) : (
        <p role="status" className="text-dark font-semibold">{t("preparation")}</p>
      )}
    </div>
  );
}
