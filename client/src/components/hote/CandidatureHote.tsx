"use client";

import { useQuery } from "@tanstack/react-query";
import axios from "axios";
import { useTranslations } from "next-intl";
import { CheckCircle2, Circle, Clock, XCircle } from "lucide-react";
import { Link } from "@/i18n/navigation";
import api from "@/lib/api";
import { cn } from "@/lib/utils";
import VerificationIdentite from "@/components/hote/VerificationIdentite";
import type { ContratPublic } from "@/types/api/contrat";
import type { Me } from "@/types/api/models";

type StatutPiece = "absente" | "soumise" | "verifiee" | "refusee";
type Etat = "fait" | "attente" | "refuse" | "a_faire";

const ICONES: Record<Etat, { icone: typeof Circle; classe: string }> = {
  fait: { icone: CheckCircle2, classe: "text-green-600" },
  attente: { icone: Clock, classe: "text-amber-500" },
  refuse: { icone: XCircle, classe: "text-red-600" },
  a_faire: { icone: Circle, classe: "text-gray-300" },
};

/** Steps to become a host: phone, identity document (checked before any visit), then visited listing.
 *  Shown while the identity is not verified; afterwards, a simple "Identity verified" mention. */
export default function CandidatureHote({ nbAnnonces, onNouvelle }: { nbAnnonces: number; onNouvelle: () => void }) {
  const t = useTranslations("espaceHote.candidature");
  const { data: me } = useQuery({
    queryKey: ["me"],
    queryFn: async () => (await api.get<Me>("/v1/users/me/")).data,
  });
  const { data: piece } = useQuery({
    queryKey: ["verification", "identite"],
    queryFn: async () => (await api.get<{ statut: StatutPiece }>("/v1/verifications/identite/")).data,
  });
  // null: agreement not offered yet (Kwa-Ba has not filled in its legal information), step hidden
  const { data: contrat } = useQuery({
    queryKey: ["contrat-hote"],
    queryFn: async () => {
      try {
        return (await api.get<ContratPublic>("/v1/contrats/hote/")).data;
      } catch (err) {
        if (axios.isAxiosError(err) && err.response?.status === 404) return null;
        throw err;
      }
    },
  });

  if (!me || !piece || contrat === undefined) return null;
  const contratASigner = contrat !== null && contrat.statut !== "signe";
  if (piece.statut === "verifiee" && !contratASigner) return <VerificationIdentite />;

  const etapes: { cle: string; etat: Etat; titre: string; texte: React.ReactNode }[] = [
    {
      cle: "telephone",
      etat: me.phone ? "fait" : "a_faire",
      titre: t("telephoneTitre"),
      texte: me.phone ? me.phone : (
        <>{t("telephoneTexte")} <Link href="/profil/edit" className="font-bold text-primary underline">{t("telephoneAction")}</Link></>
      ),
    },
    {
      cle: "identite",
      etat: piece.statut === "verifiee" ? "fait" : piece.statut === "soumise" ? "attente" : piece.statut === "refusee" ? "refuse" : "a_faire",
      titre: t("identiteTitre"),
      texte: piece.statut === "verifiee" ? t("identiteVerifiee") : piece.statut === "soumise" ? t("identiteEnCours")
        : piece.statut === "refusee" ? t("identiteRefusee") : t("identiteTexte"),
    },
    ...(contrat ? [{
      cle: "contrat",
      etat: (contrat.statut === "signe" ? "fait" : "a_faire") as Etat,
      titre: t("contratTitre"),
      texte: (
        <>
          {contrat.statut === "signe" ? t("contratSigne") : t("contratTexte")}{" "}
          <Link href="/hote/espace/contrat" className="font-bold text-primary underline">
            {contrat.statut === "signe" ? t("contratTelecharger") : t("contratAction")}
          </Link>
        </>
      ),
    }] : []),
    {
      cle: "annonce",
      etat: nbAnnonces > 0 ? "attente" : "a_faire",
      titre: t("annonceTitre"),
      texte: nbAnnonces > 0 ? (contrat ? t("annonceContrat") : t("annonceEnAttente")) : (
        <>{t("annonceTexte")} <button type="button" onClick={onNouvelle} className="font-bold text-primary underline">{t("annonceAction")}</button></>
      ),
    },
  ];

  return (
    <section className="bg-white rounded-3xl border border-gray-100 shadow-sm p-5 sm:p-6 mb-8">
      <h2 className="font-heading font-bold text-lg text-dark">{t("titre", { nombre: etapes.length })}</h2>
      <p className="text-sm text-gray-500 mt-1">{t("texte")}</p>
      <ol className="mt-5 space-y-4">
        {etapes.map((etape, i) => {
          const { icone: Icone, classe } = ICONES[etape.etat];
          return (
            <li key={etape.cle} className="flex gap-3">
              <Icone size={22} className={cn("flex-shrink-0 mt-0.5", classe)} aria-hidden />
              <div className="min-w-0">
                <p className="font-semibold text-dark text-sm">{i + 1}. {etape.titre}</p>
                <p className="text-sm text-gray-600 mt-0.5">{etape.texte}</p>
              </div>
            </li>
          );
        })}
      </ol>
      {piece.statut !== "verifiee" && (
        <div className="mt-6">
          <VerificationIdentite />
        </div>
      )}
    </section>
  );
}
