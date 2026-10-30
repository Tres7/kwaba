"use client";

import { Link, usePathname } from "@/i18n/navigation";
import { useState } from "react";
import { useSession } from "next-auth/react";
import { CalendarClock, CreditCard, Lock, ShieldCheck, Smartphone, Wallet } from "lucide-react";
import api, { apiErrorMessage } from "@/lib/api";
import { calculerDon, dateReversement, useConfigGive } from "@/lib/give";
import { enEuros, versPagePaiement } from "@/lib/paiement";
import { cn, formatDate, formatFcfa } from "@/lib/utils";
import type { OrganisationDetail } from "@/types/api/give";
import type { MoyenPaiement } from "@/types/api/paiement";
import { useTranslations } from "next-intl";

const MOYENS: { id: MoyenPaiement; label: string; icon: typeof Smartphone }[] = [
  { id: "mobile_money", label: "mobileMoney", icon: Smartphone },
  { id: "carte", label: "carte", icon: CreditCard },
  { id: "paypal", label: "paypal", icon: Wallet },
];

/** Choice of the amount, fees and payment method; everything about the donation is shown before paying. */
export default function FormulaireDon({ organisation, projetId }: { organisation: OrganisationDetail; projetId: string | null }) {
  const t = useTranslations("don");
  const tRes = useTranslations("reservation");
  const pathname = usePathname();
  const { status } = useSession();
  const { data: config } = useConfigGive();
  const [montant, setMontant] = useState(2000);
  const [libre, setLibre] = useState("");
  const [couvreFrais, setCouvreFrais] = useState(true);
  const [partage, setPartage] = useState(false);
  const [moyen, setMoyen] = useState<MoyenPaiement | null>(null);
  const [envoi, setEnvoi] = useState(false);
  const [erreur, setErreur] = useState("");

  if (!config) return <div className="h-96 skeleton rounded-3xl" />;

  const projet = organisation.projets.find((p) => p.id === projetId) ?? null;
  const valeur = libre ? Number(libre) : montant;
  const valide = Number.isInteger(valeur) && valeur >= config.montant_min && valeur <= config.montant_max;
  const calcul = calculerDon(valide ? valeur : 0, couvreFrais, config.frais_paiement);
  const fraisAjoutes = calculerDon(valide ? valeur : 0, true, config.frais_paiement).frais;
  const moyensDispo = MOYENS.filter((m) => config.moyens.includes(m.id));
  const moyenChoisi = moyen && moyensDispo.some((m) => m.id === moyen) ? moyen : moyensDispo[0]?.id;
  const euros = (fcfa: number) => enEuros(fcfa, config.fcfa_par_euro);

  const donner = async () => {
    if (!valide || !moyenChoisi) return;
    setEnvoi(true);
    setErreur("");
    try {
      const res = await api.post<{ id: string; url: string }>("/v1/give/dons/", {
        organisation: organisation.slug, projet: projet?.id ?? null, montant: valeur,
        couvre_frais: couvreFrais, moyen: moyenChoisi, partage_identite: partage,
      });
      versPagePaiement(res.data.url);
    } catch (err) {
      setErreur(apiErrorMessage(err, t("erreurDemarrage")));
      setEnvoi(false);
    }
  };

  return (
    <section id="don" aria-labelledby="don-titre" className="bg-white rounded-3xl border border-gray-100 shadow-card p-5 sm:p-6 space-y-5 scroll-mt-24">
      <div>
        <h2 id="don-titre" className="font-heading font-bold text-dark text-xl">{t("titre")}</h2>
        <p className="text-sm text-gray-600 mt-1">
          {t.rich("beneficiaire", { nom: organisation.nom, strong: (x) => <strong className="text-dark">{x}</strong> })}{projet && <>, {t("projet", { titre: projet.titre })}</>}
        </p>
      </div>

      <fieldset>
        <legend className="text-sm font-bold text-dark mb-2">{t("montant")}</legend>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {config.montants_suggeres.map((m) => {
            const actif = !libre && montant === m;
            return (
              <button key={m} type="button" aria-pressed={actif} onClick={() => { setMontant(m); setLibre(""); }}
                className={cn("rounded-xl border-2 py-2.5 px-2 text-center transition-colors",
                  actif ? "border-primary bg-primary/5" : "border-gray-200 hover:border-primary/40")}>
                <span className="block font-bold text-dark text-sm">{formatFcfa(m)}</span>
                <span className="block text-xs text-gray-600">≈ {euros(m)}</span>
              </button>
            );
          })}
        </div>
        <label htmlFor="don-libre" className="block text-sm text-dark mt-3">{t("autreMontant")}</label>
        <input id="don-libre" type="number" inputMode="numeric" min={config.montant_min} max={config.montant_max} step={1}
          value={libre} onChange={(e) => setLibre(e.target.value.replace(/\D/g, ""))} placeholder={t("desMontant", { montant: config.montant_min })}
          aria-describedby="don-libre-aide"
          className="mt-1 w-full sm:w-60 rounded-xl border border-gray-200 px-4 py-2.5 text-dark focus:border-primary focus:outline-none" />
        <p id="don-libre-aide" className={cn("text-xs mt-1", libre && !valide ? "text-red-700" : "text-gray-600")}>
          {libre && !valide
            ? `Entre ${formatFcfa(config.montant_min)} et ${formatFcfa(config.montant_max)}.`
            : libre ? `≈ ${euros(valeur)}` : t("montantLibre")}
        </p>
      </fieldset>

      <label className="flex items-start gap-3 rounded-2xl bg-light p-4 cursor-pointer">
        <input type="checkbox" checked={couvreFrais} onChange={(e) => setCouvreFrais(e.target.checked)} className="mt-1 accent-primary w-4 h-4" />
        <span className="text-sm text-dark">
          {t.rich("ajouterFrais", { frais: formatFcfa(fraisAjoutes), nom: organisation.nom, strong: (x) => <strong>{x}</strong> })}
          <span className="block text-xs text-gray-600 mt-0.5">
            {t("fraisExplication", { taux: Math.round(config.frais_paiement * 100) })}
          </span>
        </span>
      </label>

      <div className="rounded-2xl border border-gray-100 divide-y divide-gray-100 text-sm" aria-live="polite">
        <h3 className="px-4 py-3 font-heading font-bold text-dark">{t("avantDePayer")}</h3>
        <dl className="px-4 py-3 space-y-1.5">
          <div className="flex justify-between gap-3"><dt className="text-gray-600">{t("beneficiaireCourt")}</dt><dd className="font-semibold text-dark text-right">{organisation.nom}</dd></div>
          <div className="flex justify-between gap-3"><dt className="text-gray-600">{t("votreDon")}</dt><dd className="text-dark">{formatFcfa(valide ? valeur : 0)}</dd></div>
          <div className="flex justify-between gap-3">
            <dt className="text-gray-600">{t("fraisPaiement")}</dt>
            <dd className="text-dark">{couvreFrais ? `+ ${formatFcfa(calcul.frais)}` : t("deduits", { montant: formatFcfa(calcul.frais) })}</dd>
          </div>
          <div className="flex justify-between gap-3"><dt className="text-gray-600">{t("commission")}</dt><dd className="text-dark">0 FCFA</dd></div>
          <div className="flex justify-between gap-3 pt-1.5 border-t border-gray-100">
            <dt className="font-bold text-dark">{t("vousPayez")}</dt>
            <dd className="font-bold text-dark">{formatFcfa(calcul.total)}{moyenChoisi === "paypal" && <> ({euros(calcul.total)})</>}</dd>
          </div>
          <div className="flex justify-between gap-3"><dt className="font-bold text-primary">{t("ongRecoit")}</dt><dd className="font-bold text-primary">{formatFcfa(calcul.montantOng)}</dd></div>
        </dl>
        <p className="flex gap-2 px-4 py-3 text-gray-600">
          <CalendarClock size={16} className="text-primary flex-shrink-0 mt-0.5" />
          <span>{t.rich("calendrier", { date: formatDate(dateReversement(config.jour_reversement).toISOString()), strong: (x) => <strong className="text-dark">{x}</strong> })}</span>
        </p>
        <p className="flex gap-2 px-4 py-3 text-gray-600">
          <ShieldCheck size={16} className="text-primary flex-shrink-0 mt-0.5" />
          <span>
            {t("donnees")}{" "}
            <Link href="/confidentialite" className="font-semibold text-primary hover:underline">{t("politique")}</Link>
          </span>
        </p>
      </div>

      <label className="flex items-start gap-3 cursor-pointer text-sm text-dark">
        <input type="checkbox" checked={partage} onChange={(e) => setPartage(e.target.checked)} className="mt-1 accent-primary w-4 h-4" />
        <span>{t("partageIdentite", { nom: organisation.nom })}</span>
      </label>

      {status !== "authenticated" ? (
        <Link href={`/login?callbackUrl=${encodeURIComponent(`${pathname}#don`)}`}
          className="flex items-center justify-center w-full bg-secondary text-white font-bold py-3.5 rounded-xl hover:bg-secondary/90">
          {t("seConnecter")}
        </Link>
      ) : !config.actif || moyensDispo.length === 0 ? (
        <p className="text-sm text-amber-800 bg-amber-50 rounded-xl p-3">{t("indisponible")}</p>
      ) : (
        <>
          <fieldset>
            <legend className="text-sm font-bold text-dark mb-2">{t("payerAvec")}</legend>
            <div className="grid grid-cols-3 gap-2">
              {moyensDispo.map(({ id, label, icon: Icon }) => (
                <button key={id} type="button" aria-pressed={moyenChoisi === id} onClick={() => setMoyen(id)}
                  className={cn("flex flex-col items-center gap-1 rounded-xl border-2 py-2.5 text-xs font-bold transition-colors",
                    moyenChoisi === id ? "border-primary bg-primary/5 text-primary" : "border-gray-200 text-dark hover:border-primary/40")}>
                  <Icon size={18} /> {tRes(`moyens.${label}`)}
                </button>
              ))}
            </div>
          </fieldset>
          {erreur && <p role="alert" className="text-sm text-red-700 bg-red-50 rounded-xl p-3">{erreur}</p>}
          <button type="button" onClick={donner} disabled={!valide || envoi}
            className="flex items-center justify-center gap-2 w-full bg-secondary text-white font-bold py-3.5 rounded-xl hover:bg-secondary/90 disabled:opacity-60">
            <Lock size={16} /> {envoi ? t("redirection") : t("donner", { montant: formatFcfa(calcul.total) })}
          </button>
          <p className="text-xs text-gray-600 text-center">{t("securise", { prestataire: moyenChoisi === "paypal" ? "PayPal" : "FedaPay" })}</p>
        </>
      )}
    </section>
  );
}
