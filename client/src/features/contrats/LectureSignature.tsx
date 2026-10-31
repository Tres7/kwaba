"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { AlertTriangle, CheckCircle2, FileDown, Loader2, PenLine } from "lucide-react";
import { toast } from "sonner";
import { messageErreurPdf } from "@/lib/documents";
import { apiErrorMessage, estErreurApi } from "@/lib/api";
import PadSignature from "./PadSignature";
import type { ContratPublic, SignatureContrat } from "./types";
import { useFormat } from "@/lib/format";

/** Reading the contract then signing: typed name, drawn signature, express consent. */
export default function LectureSignature({ contrat, onSigner, onTelecharger }: {
  contrat: ContratPublic;
  onSigner: (donnees: SignatureContrat) => Promise<void>;
  onTelecharger: () => Promise<void>;
}) {
  const { formatDate, langue } = useFormat();
  const t = useTranslations("contrat");
  const [nom, setNom] = useState("");
  const [signature, setSignature] = useState<string | null>(null);
  const [accepte, setAccepte] = useState(false);
  const [envoi, setEnvoi] = useState(false);
  const [telechargement, setTelechargement] = useState(false);
  const [erreur, setErreur] = useState("");

  const signe = contrat.statut === "signe";
  const quand = (d: string | null) => (d ? formatDate(d, { day: "numeric", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit" }) : "");

  const telecharger = async () => {
    setTelechargement(true);
    try {
      await onTelecharger();
    } catch (err) {
      toast.error(await messageErreurPdf(err));
    } finally {
      setTelechargement(false);
    }
  };

  const signer = async () => {
    setErreur("");
    if (nom.trim().length < 3) return setErreur(t("erreurNom"));
    if (!signature) return setErreur(t("erreurSignature"));
    if (!accepte) return setErreur(t("erreurAccepte"));
    setEnvoi(true);
    try {
      await onSigner({ nom: nom.trim(), signature, accepte });
    } catch (err) {
      setErreur(estErreurApi(err) || !(err instanceof Error) ? apiErrorMessage(err) : err.message);
    } finally {
      setEnvoi(false);
    }
  };

  return (
    <div className="space-y-5">
      <header>
        <p className="text-xs font-bold uppercase tracking-wide text-primary">{t("surtitre")}</p>
        <h1 className="font-heading font-bold text-2xl sm:text-3xl text-dark mt-1">{contrat.titre}</h1>
        <p className="text-sm text-gray-600 mt-1">
          {contrat.reference ? `${t("reference")} ${contrat.reference} · ` : ""}{t("pour", { nom: contrat.partie_nom })}
        </p>
      </header>

      {signe && (
        <div role="status" className="flex gap-3 bg-green-50 border border-green-200 text-green-900 rounded-2xl p-4">
          <CheckCircle2 size={22} className="flex-shrink-0 text-green-600" aria-hidden />
          <div>
            <p className="font-bold">{t("signeTitre")}</p>
            <p className="text-sm mt-0.5">{t("signeTexte", { nom: contrat.signataire_nom, date: quand(contrat.signe_le) })}</p>
          </div>
        </div>
      )}
      {contrat.expire && (
        <div role="alert" className="flex gap-3 bg-amber-50 border border-amber-200 text-amber-900 rounded-2xl p-4">
          <AlertTriangle size={22} className="flex-shrink-0" aria-hidden />
          <p className="text-sm">{t("expire")}</p>
        </div>
      )}
      {langue() === "en" && <p className="text-sm text-gray-600 bg-gray-50 rounded-xl px-4 py-3">{t("enFrancais")}</p>}

      <article aria-label={contrat.titre} tabIndex={0}
        className="bg-white rounded-3xl border border-gray-100 shadow-sm p-5 sm:p-8 max-h-[65vh] overflow-y-auto focus:outline-none focus-visible:ring-2 focus-visible:ring-primary" lang="fr">
        {contrat.blocs.map((b, i) => b.type === "titre"
          ? <h2 key={i} className="font-heading font-bold text-primary text-base mt-5 first:mt-0 mb-1.5">{b.texte}</h2>
          : <p key={i} className="text-sm text-dark leading-relaxed mb-3 whitespace-pre-line text-justify">{b.texte}</p>)}
      </article>

      {/* Host agreement not issued yet (it is at signature): no PDF yet */}
      {contrat.reference && (
        <button type="button" onClick={telecharger} disabled={telechargement}
          className="inline-flex items-center gap-2 min-h-[44px] px-4 rounded-full border border-gray-200 bg-white text-sm font-semibold text-dark hover:border-primary hover:text-primary disabled:opacity-60">
          {telechargement ? <Loader2 size={16} className="animate-spin" aria-hidden /> : <FileDown size={16} aria-hidden />}
          {signe ? t("telechargerSigne") : t("telechargerProjet")}
        </button>
      )}

      {!signe && !contrat.expire && contrat.statut === "a_signer" && (
        <form method="post" onSubmit={(e) => { e.preventDefault(); if (!envoi) signer(); }}
          className="bg-white rounded-3xl border border-gray-100 shadow-sm p-5 sm:p-6 space-y-5">
          <h2 className="font-heading font-bold text-lg text-dark flex items-center gap-2"><PenLine size={20} className="text-primary" aria-hidden /> {t("signerTitre")}</h2>
          <label className="block">
            <span className="block text-sm font-semibold text-dark mb-1.5">{t("nomComplet")}</span>
            <input value={nom} onChange={(e) => setNom(e.target.value)} autoComplete="name" placeholder={contrat.partie_nom}
              className="w-full px-4 py-3 bg-white border border-gray-200 rounded-xl text-base text-dark focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary" />
          </label>
          <div>
            <span className="block text-sm font-semibold text-dark mb-1.5" id="libelle-signature">{t("votreSignature")}</span>
            <PadSignature onChange={setSignature} nom={nom} desactive={envoi} />
          </div>
          <label className="flex gap-3 items-start cursor-pointer">
            <input type="checkbox" checked={accepte} onChange={(e) => setAccepte(e.target.checked)} className="accent-primary w-5 h-5 mt-0.5 flex-shrink-0" />
            <span className="text-sm text-dark">{t("consentement")}</span>
          </label>
          {erreur && <p role="alert" className="text-sm text-red-600">{erreur}</p>}
          <button type="submit" disabled={envoi}
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 min-h-[48px] px-8 rounded-xl bg-secondary text-white font-bold hover:bg-secondary-600 disabled:opacity-60">
            {envoi && <Loader2 size={18} className="animate-spin" aria-hidden />}
            {envoi ? t("signatureEnCours") : t("signer")}
          </button>
          <p className="text-xs text-gray-500">{t("preuves")}</p>
        </form>
      )}
    </div>
  );
}
