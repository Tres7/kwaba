"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSession } from "next-auth/react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { Link, usePathname, useRouter } from "@/i18n/navigation";
import { apiErrorMessage } from "@/lib/api";
import Select from "@/components/ui/Select";
import Stepper from "@/components/ui/Stepper";
import { cn, isoDate } from "@/lib/utils";
import { useFormat } from "@/lib/format";
import { calculerDevisLocation, creerLocation, listerMesChauffeurs, listerMesReservations } from "./api";
import type { CatalogueLocation, CategorieVehicule, Formule } from "./types";

const inputClass = "w-full px-4 py-3 bg-white border border-gray-200 rounded-xl text-base sm:text-sm text-dark placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary";

const labelClass = "block text-xs font-bold text-dark uppercase tracking-wide mb-2";

/** Local date and time in the datetime-local field format, `jours` days from now. */
function dansJours(jours: number, heure = "10:00") {
  const d = new Date();
  d.setDate(d.getDate() + jours);
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${heure}`;
}

export default function FormulaireLocation({ catalogue, categorie, formule, onChanger }: {
  catalogue: CatalogueLocation; categorie: CategorieVehicule | null; formule: Formule; onChanger: () => void;
}) {
  const { formatDate, formatPrice } = useFormat();
  const t = useTranslations("location");
  const router = useRouter();
  const pathname = usePathname();
  const { status } = useSession();
  const lieux = catalogue.lieux ?? [];
  const regles = catalogue.regles!;
  const avecChauffeur = formule !== "sans_chauffeur";
  const [lieuPrise, setLieuPrise] = useState(String(lieux[0]?.id ?? ""));
  const [lieuRetour, setLieuRetour] = useState(String(lieux[0]?.id ?? ""));
  const [adressePrise, setAdressePrise] = useState("");
  const [adresseRetour, setAdresseRetour] = useState("");
  const [debut, setDebut] = useState(dansJours(regles.delai_min_jours + 1));
  const [fin, setFin] = useState(dansJours(regles.delai_min_jours + 4));
  const placesMax = categorie?.places ?? 8;
  const [passagers, setPassagers] = useState(Math.min(2, placesMax));
  const [telephone, setTelephone] = useState("");
  const [precisions, setPrecisions] = useState("");
  const [conducteur, setConducteur] = useState("");
  const [permisNumero, setPermisNumero] = useState("");
  const [permisPays, setPermisPays] = useState("");
  const [horsLome, setHorsLome] = useState(0);
  const [horsPays, setHorsPays] = useState(0);
  const [chauffeurDemande, setChauffeurDemande] = useState("");
  const [sejour, setSejour] = useState("");
  const [accepte, setAccepte] = useState(false);
  const [envoi, setEnvoi] = useState(false);

  const prise = lieux.find((l) => String(l.id) === lieuPrise);
  const retour = lieux.find((l) => String(l.id) === lieuRetour);
  const optionsLieux = lieux.map((l) => ({ value: String(l.id), label: l.nom, hint: l.frais && formule !== "chauffeur_seul" ? `+ ${formatPrice(l.frais)}` : undefined }));

  // "My driver" and Stay Pack: only for a signed-in traveller
  const mesChauffeurs = useQuery({
    queryKey: ["location", "mes-chauffeurs"],
    queryFn: listerMesChauffeurs,
    enabled: status === "authenticated" && avecChauffeur,
  });
  const sejours = useQuery({
    queryKey: ["reservations", "a-venir"],
    queryFn: async () => (await listerMesReservations()).filter((r) => r.status === "confirmed" && r.check_in > isoDate()),
    enabled: status === "authenticated",
  });

  const devis = useQuery({
    queryKey: ["location", "devis", categorie?.id, formule, lieuPrise, lieuRetour, debut, fin, horsLome, horsPays],
    queryFn: () => calculerDevisLocation({
      categorie: categorie?.id, formule, lieu_prise: lieuPrise, lieu_retour: lieuRetour, debut, fin,
      jours_hors_lome: horsLome, jours_hors_pays: horsPays,
    }),
    enabled: !!(lieuPrise && debut && fin),
    retry: false,
  });

  const reserver = async (e: React.FormEvent) => {
    e.preventDefault();
    if (status !== "authenticated") {
      router.push(`/login?callbackUrl=${encodeURIComponent(pathname)}`);
      return;
    }
    setEnvoi(true);
    try {
      const location = await creerLocation({
        categorie: categorie?.id ?? null, formule, lieu_prise: Number(lieuPrise), lieu_retour: Number(lieuRetour),
        adresse_prise: adressePrise, adresse_retour: adresseRetour, debut, fin, passagers, telephone, precisions,
        conducteur, permis_numero: permisNumero, permis_pays: permisPays,
        jours_hors_lome: avecChauffeur ? horsLome : 0, jours_hors_pays: avecChauffeur ? horsPays : 0,
        chauffeur_demande: chauffeurDemande ? Number(chauffeurDemande) : null, reservation: sejour || null,
      });
      router.push(`/location/${location.id}`);
    } catch (err) {
      toast.error(apiErrorMessage(err));
      setEnvoi(false);
    }
  };

  const erreurDevis = devis.error ? apiErrorMessage(devis.error) : null;
  const d = devis.data;

  return (
    <form method="post" onSubmit={reserver} className="bg-white rounded-3xl border border-gray-100 shadow-sm p-5 sm:p-8 space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="font-heading font-bold text-dark text-xl">{categorie ? t("reserverTitre", { nom: categorie.nom }) : t("chauffeurSeulTitre")}</h2>
          <p className="text-sm text-gray-500">{t(`formules.${formule}`)}{categorie?.exemple_modele ? ` · ${categorie.exemple_modele}` : ""}</p>
        </div>
        <button type="button" onClick={onChanger} className="text-sm font-semibold text-primary hover:underline">{categorie ? t("changer") : t("changerFormule")}</button>
      </div>

      <p className="text-sm bg-amber-50 text-amber-900 rounded-xl px-4 py-3">{t("delai", { jours: regles.delai_min_jours })}</p>
      {formule === "chauffeur_seul" && <p className="text-sm bg-gray-50 text-gray-700 rounded-xl px-4 py-3">{t("chauffeurSeulAide")}</p>}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {([["prise", lieuPrise, setLieuPrise, prise, adressePrise, setAdressePrise, debut, setDebut],
           ["retour", lieuRetour, setLieuRetour, retour, adresseRetour, setAdresseRetour, fin, setFin]] as const).map(
          ([cle, lieu, setLieu, detail, adresse, setAdresse, date, setDate]) => (
            <fieldset key={cle} className="space-y-3">
              <legend className="font-heading font-bold text-dark mb-1">{formule === "chauffeur_seul" ? t(cle === "prise" ? "debutMission" : "finMission") : t(cle)}</legend>
              <div>
                <p className={labelClass}>{t("lieu")}</p>
                <Select label={t(cle)} value={lieu} onChange={setLieu} options={optionsLieux} />
              </div>
              {detail?.adresse_requise && (
                <label className="block">
                  <span className={labelClass}>{t("adresse")}</span>
                  <input className={inputClass} value={adresse} onChange={(e) => setAdresse(e.target.value)} placeholder={t("adressePlaceholder")} required maxLength={255} />
                </label>
              )}
              <label className="block">
                <span className={labelClass}>{t("dateHeure")}</span>
                <input type="datetime-local" className={inputClass} value={date} min={dansJours(regles.delai_min_jours, "00:00")}
                  onChange={(e) => setDate(e.target.value)} required />
              </label>
            </fieldset>
          ),
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
        <div>
          <p className={labelClass}>{t("passagers")}</p>
          <Stepper className="border border-gray-200 rounded-xl px-4 py-2.5 bg-white" label={t("passagers")} value={passagers}
            min={1} max={placesMax} onChange={setPassagers} />
        </div>
        <label className="block">
          <span className={labelClass}>{t("telephone")}</span>
          <input type="tel" className={inputClass} value={telephone} onChange={(e) => setTelephone(e.target.value)} placeholder="+228 90 00 00 00" required />
        </label>
      </div>

      {avecChauffeur && (
        <fieldset className="space-y-3">
          <legend className="font-heading font-bold text-dark mb-1">{t("chauffeurTitre")}</legend>
          <p className="text-sm text-gray-600">{t("chauffeurConditions", { prix: formatPrice(catalogue.chauffeur?.prix_jour ?? 7000), heure: formatPrice(catalogue.chauffeur?.heure_sup ?? 1000) })}</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <p className={labelClass}>{t("joursHorsLome", { prime: formatPrice(catalogue.chauffeur?.prime_hors_lome ?? 1500) })}</p>
              <Stepper className="border border-gray-200 rounded-xl px-4 py-2.5 bg-white" label={t("joursHorsLomeCourt")} value={horsLome} min={0} max={60} onChange={setHorsLome} />
            </div>
            <div>
              <p className={labelClass}>{t("joursHorsPays", { prime: formatPrice(catalogue.chauffeur?.prime_hors_pays ?? 2000) })}</p>
              <Stepper className="border border-gray-200 rounded-xl px-4 py-2.5 bg-white" label={t("joursHorsPaysCourt")} value={horsPays} min={0} max={60} onChange={setHorsPays} />
            </div>
          </div>
          {!!mesChauffeurs.data?.length && (
            <div>
              <p className={labelClass}>{t("monChauffeur")}</p>
              <Select label={t("monChauffeur")} value={chauffeurDemande} onChange={setChauffeurDemande}
                options={[{ value: "", label: t("monChauffeurAucun") }, ...mesChauffeurs.data.map((c) => ({ value: String(c.id), label: c.nom }))]} />
              <p className="text-xs text-gray-500 mt-1.5">{t("monChauffeurAide")}</p>
            </div>
          )}
        </fieldset>
      )}

      {formule === "sans_chauffeur" && (
        <fieldset className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <legend className="font-heading font-bold text-dark mb-3 sm:col-span-3">{t("conducteurTitre")}</legend>
          <label className="block"><span className={labelClass}>{t("conducteur")}</span><input className={inputClass} value={conducteur} onChange={(e) => setConducteur(e.target.value)} required maxLength={120} /></label>
          <label className="block"><span className={labelClass}>{t("permisNumero")}</span><input className={inputClass} value={permisNumero} onChange={(e) => setPermisNumero(e.target.value)} required maxLength={40} /></label>
          <label className="block"><span className={labelClass}>{t("permisPays")}</span><input className={inputClass} value={permisPays} onChange={(e) => setPermisPays(e.target.value)} required maxLength={60} /></label>
        </fieldset>
      )}

      {!!sejours.data?.length && (
        <div>
          <p className={labelClass}>{t("sejour")}</p>
          <Select label={t("sejour")} value={sejour} onChange={setSejour}
            options={[{ value: "", label: t("sejourAucun") }, ...sejours.data.map((r) => ({ value: r.id, label: `${r.hebergement_detail.name} · ${formatDate(r.check_in)}` }))]} />
          {avecChauffeur && <p className="text-xs text-secondary font-semibold mt-1.5">{t("packSejour")}</p>}
        </div>
      )}

      <label className="block">
        <span className={labelClass}>{t("precisions")}</span>
        <span className="block text-xs text-gray-500 -mt-1 mb-2">{formule === "chauffeur_seul" ? t("precisionsAideChauffeur") : t("precisionsAide")}</span>
        <textarea rows={4} className={cn(inputClass, "resize-y")} value={precisions} onChange={(e) => setPrecisions(e.target.value)}
          placeholder={t("precisionsPlaceholder")} required minLength={15} maxLength={2000} />
      </label>

      <div className="text-sm text-gray-600 bg-gray-50 rounded-xl px-4 py-3 space-y-1">
        <p className="font-bold text-dark">{t("conditions")}</p>
        {regles.conditions && formule === "sans_chauffeur" && <p className="whitespace-pre-line">{regles.conditions}</p>}
        <p>{t("annulationRegle", { heures: regles.annulation_gratuite_heures })}</p>
      </div>

      <div className="border-t border-gray-100 pt-5" aria-live="polite">
        {devis.isFetching ? (
          <p className="text-sm text-gray-500">{t("calcul")}</p>
        ) : erreurDevis ? (
          <p role="alert" className="text-sm text-red-700 bg-red-50 rounded-xl px-4 py-3">{erreurDevis}</p>
        ) : d ? (
          <dl className="space-y-1 text-sm">
            {d.prix_vehicule > 0 && <div className="flex justify-between"><dt className="text-gray-600">{t("devisJours", { nombre: d.jours, prix: formatPrice(d.prix_jour) })}</dt><dd>{formatPrice(d.prix_vehicule)}</dd></div>}
            {d.prix_chauffeur > 0 && <div className="flex justify-between"><dt className="text-gray-600">{t("devisChauffeur", { nombre: d.jours })}</dt><dd>{formatPrice(d.prix_chauffeur)}</dd></div>}
            {d.primes > 0 && <div className="flex justify-between"><dt className="text-gray-600">{t("devisPrimes")}</dt><dd>{formatPrice(d.primes)}</dd></div>}
            {d.frais_lieux > 0 && <div className="flex justify-between"><dt className="text-gray-600">{t("frais")}</dt><dd>{formatPrice(d.frais_lieux)}</dd></div>}
            {d.caution_en_ligne && <div className="flex justify-between"><dt className="text-gray-600">{t("cautionLigne")}</dt><dd>{formatPrice(d.caution)}</dd></div>}
            <div className="flex justify-between pt-2 font-heading font-bold text-dark text-lg"><dt>{t("total")}</dt><dd>{formatPrice(d.a_payer)}</dd></div>
            {formule !== "chauffeur_seul" && <p className="text-xs text-gray-500 pt-1">{t("sansFrais")}</p>}
            {d.caution_en_ligne ? (
              <p className="text-xs text-gray-500 pt-1">{t("cautionEnLigne", { heures: regles.restitution_caution_heures })}</p>
            ) : d.caution > 0 && <p className="text-xs text-gray-500 pt-1">{t("caution", { montant: formatPrice(d.caution) })}</p>}
          </dl>
        ) : null}

        <label className="flex items-start gap-2.5 text-xs text-gray-600 leading-relaxed mt-5 cursor-pointer">
          <input type="checkbox" checked={accepte} onChange={(e) => setAccepte(e.target.checked)}
            className="mt-0.5 h-4 w-4 flex-shrink-0 rounded border-gray-300 text-primary focus:ring-primary" />
          <span>{t.rich("accepter", {
            cgv: (x) => <Link href="/cgv" className="text-primary font-medium">{x}</Link>,
            annulation: (x) => <Link href="/remboursement" className="text-primary font-medium">{x}</Link>,
          })}</span>
        </label>
        <button type="submit" disabled={envoi || !d || (status === "authenticated" && !accepte)}
          className="mt-4 w-full sm:w-auto px-8 py-3.5 rounded-xl bg-secondary text-white font-bold disabled:opacity-50">
          {envoi ? t("envoi") : status === "authenticated" ? t("reserver") : t("connexion")}
        </button>
      </div>
    </form>
  );
}
