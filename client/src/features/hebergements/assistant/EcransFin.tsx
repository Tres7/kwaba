"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { CheckCircle2, Circle } from "lucide-react";
import { PreinscriptionHote } from "@/features/contrats";
import { ProfilVersementForm, useRevenus } from "@/features/paiements";
import { CLE_MOI, modifierMoi, useMoi } from "@/features/users";
import { VerificationIdentite } from "@/features/verifications";
import Select from "@/components/ui/Select";
import { Link } from "@/i18n/navigation";
import { apiErrorMessage, firstErrorMessage } from "@/lib/api";
import { useFormat } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { PolitiqueAnnulation } from "@/types/api/models";
import { useEquipements } from "../AmenityBadge";
import type { DonneesAnnonce } from "../brouillons";
import EstimateurRevenus from "../EstimateurRevenus";
import type { EcranProps } from "./Ecrans";
import { champClass, Erreur, libelleClass, Question } from "./Ecrans";

const POLITIQUES: PolitiqueAnnulation[] = ["souple", "moderee", "ferme"];
const DECLARATIONS = ["cameras", "animaux", "travaux"] as const;

export function EcranPrix({ donnees, modifier, erreurs }: EcranProps) {
  const t = useTranslations("assistantHote");
  const { data: revenus } = useRevenus();
  const prix = Number(donnees.price_per_night) || 0;
  return (
    <Question cle="prix">
      <label className="sr-only" htmlFor="a-prix">{t("prix.titre")}</label>
      <div className="flex items-baseline gap-3 border-b-2 border-primary/30 focus-within:border-primary pb-2">
        <input id="a-prix" type="number" min={1} step={500} inputMode="numeric" placeholder="35000"
          className="w-full min-w-0 bg-transparent font-heading font-bold text-4xl sm:text-5xl text-dark !outline-none placeholder:text-gray-300"
          value={donnees.price_per_night ?? ""} onChange={(e) => modifier({ price_per_night: e.target.value ? Number(e.target.value) : null })} />
        <span className="font-heading font-bold text-gray-500">FCFA</span>
      </div>
      <p className="text-sm text-gray-500 mt-2">{t("prix.parNuit")}</p>
      <Erreur messages={erreurs.price_per_night} />
      {prix > 0 && <EstimateurRevenus className="mt-5 bg-gray-50" partenaire={revenus?.partenaire ?? "particulier"} prix={prix} />}
    </Question>
  );
}

export function EcranRegles({ donnees, modifier }: EcranProps) {
  const t = useTranslations("annonce");
  const { REGLES } = useEquipements();
  const choisis = donnees.amenities ?? [];
  const choisir = (regle: (typeof REGLES)[number], valeur: string | null) => modifier({
    amenities: [...choisis.filter((a) => a !== regle.oui.id && a !== regle.non.id), ...(valeur ? [valeur] : [])],
  });
  return (
    <Question cle="regles">
      <div className="space-y-5">
        {REGLES.map((regle) => {
          const valeur = choisis.includes(regle.oui.id) ? regle.oui.id : choisis.includes(regle.non.id) ? regle.non.id : null;
          return (
            <div key={regle.id}>
              <p className={libelleClass}>{regle.label}</p>
              <div role="radiogroup" aria-label={regle.label} className="grid grid-cols-2 gap-2">
                {[regle.oui, regle.non].map((option) => (
                  <button key={option.id} type="button" role="radio" aria-checked={valeur === option.id}
                    onClick={() => choisir(regle, valeur === option.id ? null : option.id)}
                    className={cn("px-3 py-3 rounded-2xl text-sm border transition-colors",
                      valeur === option.id ? "border-primary bg-primary-50 text-primary font-semibold" : "border-gray-200 bg-white text-dark hover:border-primary/40")}>
                    {option.label}
                  </button>
                ))}
              </div>
            </div>
          );
        })}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className={libelleClass} htmlFor="a-arrivee">{t("arrivee")}</label>
            <input id="a-arrivee" type="time" className={champClass} value={donnees.arrivee_a_partir?.slice(0, 5) ?? "14:00"}
              onChange={(e) => modifier({ arrivee_a_partir: e.target.value })} />
          </div>
          <div>
            <label className={libelleClass} htmlFor="a-depart">{t("depart")}</label>
            <input id="a-depart" type="time" className={champClass} value={donnees.depart_avant?.slice(0, 5) ?? "11:00"}
              onChange={(e) => modifier({ depart_avant: e.target.value })} />
          </div>
        </div>
      </div>
    </Question>
  );
}

export function EcranAccueil({ donnees, modifier, erreurs }: EcranProps) {
  const t = useTranslations("annonce");
  const tp = useTranslations("politiqueAnnulation");
  return (
    <Question cle="accueil">
      <div className="space-y-6">
        <div>
          <p className={libelleClass} id="a-petitdej">{t("petitDejeuner")}</p>
          <div role="radiogroup" aria-labelledby="a-petitdej" className="grid grid-cols-3 gap-2">
            {(["inclus", "option", "non"] as const).map((v) => (
              <button key={v} type="button" role="radio" aria-checked={donnees.petit_dejeuner === v}
                onClick={() => modifier({ petit_dejeuner: v })}
                className={cn("px-2 py-3 rounded-2xl text-sm border transition-colors",
                  donnees.petit_dejeuner === v ? "border-primary bg-primary-50 text-primary font-semibold" : "border-gray-200 bg-white text-dark hover:border-primary/40")}>
                {t(v === "inclus" ? "petitDejInclus" : v === "option" ? "petitDejOption" : "petitDejNon")}
              </button>
            ))}
          </div>
          {donnees.petit_dejeuner === "option" && (
            <div className="mt-3">
              <label className={libelleClass} htmlFor="a-petitdej-prix">{t("petitDejPrix")}</label>
              <input id="a-petitdej-prix" type="number" min={0} step={100} inputMode="numeric" className={champClass} placeholder="3000"
                value={donnees.petit_dejeuner_prix ?? ""} onChange={(e) => modifier({ petit_dejeuner_prix: e.target.value ? Number(e.target.value) : null })} />
            </div>
          )}
          <Erreur messages={erreurs.petit_dejeuner_prix} />
        </div>
        <div>
          <label className={libelleClass} htmlFor="a-politique">{t("politique")}</label>
          <Select id="a-politique" label={t("politique")} value={donnees.politique_annulation ?? "moderee"}
            onChange={(v) => modifier({ politique_annulation: v as PolitiqueAnnulation })}
            options={POLITIQUES.map((id) => ({ value: id, label: tp(`${id}.nom`), hint: tp(`${id}.regle`) }))} />
          <p className="text-xs text-gray-500 mt-1.5">{t("politiqueAide")}</p>
        </div>
      </div>
    </Question>
  );
}

export function EcranSecurite({ donnees, modifier }: EcranProps) {
  const t = useTranslations("assistantHote.securite");
  const tAnnonce = useTranslations("annonce");
  const declarations = donnees.declarations ?? {};
  const declarer = (champs: NonNullable<DonneesAnnonce["declarations"]>) => modifier({ declarations: { ...declarations, ...champs } });
  return (
    <Question cle="securite">
      <div className="space-y-3">
        {DECLARATIONS.map((cle) => (
          <label key={cle} className="flex items-center justify-between gap-4 px-4 py-3.5 rounded-2xl border border-gray-200 cursor-pointer">
            <span className="text-sm text-dark">{t(cle)}</span>
            <input type="checkbox" className="accent-primary w-5 h-5 flex-shrink-0" checked={declarations[cle] === true}
              onChange={(e) => declarer({ [cle]: e.target.checked })} />
          </label>
        ))}
      </div>
      <label className="flex items-start gap-3 mt-6 p-4 rounded-2xl bg-primary-50 cursor-pointer">
        <input type="checkbox" className="accent-primary w-5 h-5 flex-shrink-0 mt-0.5" checked={declarations.attestation === true}
          onChange={(e) => declarer({ attestation: e.target.checked })} />
        <span className="text-sm text-dark leading-relaxed">
          {t.rich("attestation", { cgu: (x) => <Link href="/cgu#hotes" target="_blank" className="text-primary underline">{x}<span className="sr-only"> ({tAnnonce("nouvelOnglet")})</span></Link> })}
        </span>
      </label>
    </Question>
  );
}

export function EcranTelephone({ conditions }: EcranProps) {
  const t = useTranslations("assistantHote.telephone");
  const queryClient = useQueryClient();
  const { data: moi } = useMoi();
  const [numero, setNumero] = useState<string | null>(null);
  const [erreur, setErreur] = useState("");
  const [envoi, setEnvoi] = useState(false);
  const valeur = numero ?? moi?.phone ?? "";

  const enregistrer = async (e: React.FormEvent) => {
    e.preventDefault();
    setEnvoi(true);
    setErreur("");
    try {
      await modifierMoi({ phone: valeur });
      await queryClient.invalidateQueries({ queryKey: CLE_MOI });
    } catch (err) {
      const donnees = (err as { response?: { data?: { phone?: unknown } } }).response?.data;
      setErreur(firstErrorMessage(donnees?.phone) ?? apiErrorMessage(err));
    } finally {
      setEnvoi(false);
    }
  };

  return (
    <Question cle="telephone">
      <form onSubmit={enregistrer} className="space-y-3">
        <label className={libelleClass} htmlFor="a-telephone">{t("libelle")}</label>
        <input id="a-telephone" type="tel" autoComplete="tel" inputMode="tel" className={champClass} placeholder="+228 90 00 00 00"
          value={valeur} onChange={(e) => setNumero(e.target.value)} />
        <button type="submit" disabled={envoi || !valeur.trim()} className="px-5 py-3 rounded-2xl border border-primary/30 text-primary font-semibold disabled:opacity-50">
          {envoi ? t("envoi") : t("enregistrer")}
        </button>
        {erreur && <p role="alert" className="text-sm text-red-700">{erreur}</p>}
        {conditions?.telephone && <p className="flex items-center gap-2 text-sm font-semibold text-primary"><CheckCircle2 size={18} aria-hidden /> {t("fait")}</p>}
      </form>
    </Question>
  );
}

export function EcranIdentite() {
  return (
    <Question cle="identite">
      <VerificationIdentite types={["cni", "electeur", "passeport"]} />
    </Question>
  );
}

export function EcranVersement() {
  return (
    <Question cle="versement">
      <ProfilVersementForm manquant={false} />
    </Question>
  );
}

export function EcranContrat({ conditions }: EcranProps) {
  const t = useTranslations("assistantHote.contrat");
  return (
    <Question cle="contrat">
      <PreinscriptionHote onCancel={() => window.history.back()}>
        {conditions?.preinscription && <p className="flex items-center gap-2 text-sm font-semibold text-primary"><CheckCircle2 size={18} aria-hidden /> {t("accepte")}</p>}
      </PreinscriptionHote>
      {conditions?.contrat_a_signer && (
        <p className="text-sm text-gray-600 mt-5">
          {t.rich("aSigner", { lien: (x) => <Link href="/hote/espace/contrat" className="font-bold text-primary underline">{x}</Link> })}
        </p>
      )}
    </Question>
  );
}

export function EcranRecapitulatif({ donnees, conditions }: EcranProps) {
  const t = useTranslations("assistantHote.recapitulatif");
  const { TYPE_LABELS, formatPrice } = useFormat();
  const lignes = [
    ["annonce", !!conditions?.photos && !!conditions.photos_du_compte && !!conditions.attestation],
    ["telephone", !!conditions?.telephone],
    ["identite", conditions?.identite === "soumise" || conditions?.identite === "verifiee"],
    ["versement", !!conditions?.versement],
  ] as const;
  return (
    <Question cle="recapitulatif">
      <article className="rounded-3xl border border-gray-100 shadow-sm overflow-hidden">
        {donnees.image_url && <img src={donnees.image_url} alt="" className="w-full aspect-[16/9] object-cover" />}
        <div className="p-4">
          <h2 className="font-heading font-bold text-dark text-lg">{donnees.name}</h2>
          <p className="text-sm text-gray-500 mt-0.5">
            {donnees.type && TYPE_LABELS[donnees.type]} · {[donnees.location, donnees.city].filter(Boolean).join(", ")} · {t("voyageurs", { nombre: donnees.max_guests ?? 1 })}
          </p>
          <p className="font-heading font-bold text-primary mt-2">{formatPrice(Number(donnees.price_per_night) || 0)} <span className="text-sm font-normal text-gray-500">{t("parNuit")}</span></p>
        </div>
      </article>
      <ul className="mt-5 space-y-2.5">
        {lignes.map(([cle, ok]) => {
          const Icone = ok ? CheckCircle2 : Circle;
          return <li key={cle} className={cn("flex items-center gap-2.5 text-sm", ok ? "text-dark" : "text-red-700 font-semibold")}><Icone size={18} className={ok ? "text-primary" : ""} aria-hidden /> {t(`lignes.${cle}`)}</li>;
        })}
      </ul>
      <p className="text-sm text-gray-600 mt-5 bg-gray-50 rounded-2xl p-4">{t("suite")}</p>
    </Question>
  );
}
