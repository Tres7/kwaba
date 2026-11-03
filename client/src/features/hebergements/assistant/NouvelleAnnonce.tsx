"use client";

import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { House } from "lucide-react";
import { Link, useRouter } from "@/i18n/navigation";
import { apiErrorMessage, estErreurApi } from "@/lib/api";
import { creerBrouillon } from "../api";
import { TuileFlottante } from "./Decor";

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
      <TuileFlottante picto={House} phase={1} className="w-28 h-28 mb-4" />
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
