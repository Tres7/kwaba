"use client";

import { envoyerReclamation } from "@/lib/site";
import { useRef, useState } from "react";
import { useSession } from "next-auth/react";
import { useTranslations } from "next-intl";
import { CheckCircle2, Paperclip } from "lucide-react";
import { apiErrorMessage } from "@/lib/api";
import { Captcha, type CaptchaHandle } from "@/features/auth";
import FormField from "@/components/ui/FormField";
import Select from "@/components/ui/Select";

const OBJETS = ["reservation", "paiement", "logement", "transfert", "compte", "autre"] as const;
type Objet = (typeof OBJETS)[number];

/**
 * Complaint (terms of sale, art. 21.1): subject, booking number, description and optional attachment, sent
 * by email to the contact address. A visitor who is not signed in gives their email and ticks the captcha.
 */
export default function FormulaireReclamation() {
  const t = useTranslations("reclamation");
  const { status } = useSession();
  const connecte = status === "authenticated";
  const [objet, setObjet] = useState<Objet>("reservation");
  const [reservation, setReservation] = useState("");
  const [email, setEmail] = useState("");
  const [description, setDescription] = useState("");
  const [fichier, setFichier] = useState<File | null>(null);
  const [captcha, setCaptcha] = useState<string | null>(null);
  const captchaRef = useRef<CaptchaHandle>(null);
  const [etat, setEtat] = useState<"saisie" | "envoi" | "envoye">("saisie");
  const [erreur, setErreur] = useState("");

  const envoyer = async (e: React.FormEvent) => {
    e.preventDefault();
    setErreur("");
    setEtat("envoi");
    const donnees = new FormData();
    donnees.append("objet", objet);
    donnees.append("reservation", reservation.trim());
    donnees.append("description", description.trim());
    if (!connecte) donnees.append("email", email.trim());
    if (captcha) donnees.append("captcha", captcha);
    if (fichier) donnees.append("piece_jointe", fichier);
    try {
      await envoyerReclamation(donnees);
      setEtat("envoye");
    } catch (err) {
      setErreur(apiErrorMessage(err));
      captchaRef.current?.reset();
      setEtat("saisie");
    }
  };

  if (etat === "envoye") {
    return (
      <div role="status" className="flex items-start gap-3 bg-secondary/10 text-dark rounded-2xl p-5">
        <CheckCircle2 size={22} className="text-secondary flex-shrink-0 mt-0.5" />
        <div>
          <p className="font-bold">{t("accuseTitre")}</p>
          <p className="text-sm text-gray-600 mt-1">{t("accuseTexte")}</p>
        </div>
      </div>
    );
  }

  const zone = "w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-base sm:text-sm text-dark outline-none focus:ring-4 focus:ring-primary/10";
  return (
    <form method="post" onSubmit={envoyer} className="space-y-4">
      <div>
        <p className="block text-xs font-bold text-dark uppercase tracking-wide mb-2">{t("objet")}</p>
        <Select label={t("objet")} value={objet} onChange={setObjet} options={OBJETS.map((o) => ({ value: o, label: t(`objets.${o}`) }))} />
      </div>
      <FormField label={t("reservation")} name="reservation" value={reservation} onChange={(e) => setReservation(e.target.value)}
        placeholder="RES-AF2026-…" hint={t("reservationAide")} maxLength={40} />
      {!connecte && (
        <FormField label={t("email")} name="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" />
      )}
      <div>
        <label htmlFor="description-reclamation" className="block text-xs font-bold text-dark uppercase tracking-wide mb-2">{t("description")}</label>
        <textarea id="description-reclamation" required minLength={20} maxLength={4000} rows={5} value={description}
          onChange={(e) => setDescription(e.target.value)} placeholder={t("descriptionAide")} className={zone} />
      </div>
      <div>
        <label htmlFor="piece-reclamation" className="flex items-center gap-2 text-xs font-bold text-dark uppercase tracking-wide mb-2">
          <Paperclip size={14} /> {t("pieceJointe")}
        </label>
        <input id="piece-reclamation" type="file" accept="image/jpeg,image/png,image/webp,application/pdf"
          onChange={(e) => setFichier(e.target.files?.[0] ?? null)} className="block w-full text-sm text-gray-600" />
        <p className="text-xs text-gray-500 mt-1">{t("pieceJointeAide")}</p>
      </div>
      {!connecte && <Captcha ref={captchaRef} onToken={setCaptcha} />}
      {erreur && <p role="alert" className="text-sm text-red-600">{erreur}</p>}
      <button type="submit" disabled={etat === "envoi"} className="bg-primary text-white font-bold px-6 py-3 rounded-xl hover:bg-primary-600 disabled:opacity-60">
        {etat === "envoi" ? t("envoi") : t("envoyer")}
      </button>
    </form>
  );
}
