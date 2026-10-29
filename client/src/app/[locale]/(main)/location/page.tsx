"use client";

import { useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSession } from "next-auth/react";
import { useTranslations } from "next-intl";
import PageHero from "@/components/layout/PageHero";
import { toast } from "sonner";
import { BadgeCheck, Briefcase, Car, ChevronLeft, ChevronRight, Fuel, Snowflake, UserRound, Users } from "lucide-react";
import { Link, usePathname, useRouter } from "@/i18n/navigation";
import api, { apiErrorMessage } from "@/lib/api";
import Select from "@/components/ui/Select";
import Stepper from "@/components/ui/Stepper";
import { cn, formatDate, formatPrice, isoDate } from "@/lib/utils";
import { useModule } from "@/lib/site";
import type { Reservation } from "@/types/api/models";
import type { CatalogueLocation, CategorieVehicule, DevisLocation, Formule, Location, MonChauffeur } from "@/types/api/location";

const inputClass = "w-full px-4 py-3 bg-white border border-gray-200 rounded-xl text-base sm:text-sm text-dark placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary";
const labelClass = "block text-xs font-bold text-dark uppercase tracking-wide mb-2";
// "I drive" (without a driver) is not in the launch offer: offered only if its switch is on
const FORMULES: Formule[] = ["avec_chauffeur", "sans_chauffeur", "chauffeur_seul"];

/** Local date and time in the datetime-local field format, `jours` days from now. */
function dansJours(jours: number, heure = "10:00") {
  const d = new Date();
  d.setDate(d.getDate() + jours);
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${heure}`;
}

function Puce({ actif, onClick, children }: { actif: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button type="button" aria-pressed={actif} onClick={onClick}
      className={cn("relative zone-tactile px-4 py-2 rounded-full text-sm font-semibold border transition-colors whitespace-nowrap",
        actif ? "bg-primary text-white border-primary" : "bg-white text-dark border-gray-200 hover:border-primary/40")}>
      {children}
    </button>
  );
}

/** Vehicle photos: swipe scrolling (snapping), arrows on hover on computers, position dots. */
function Galerie({ photos, nom }: { photos: string[]; nom: string }) {
  const t = useTranslations("location");
  const rail = useRef<HTMLDivElement>(null);
  const [index, setIndex] = useState(0);
  if (!photos.length) return <Car size={56} className="text-gray-300" aria-hidden />;
  const aller = (i: number) => rail.current?.scrollTo({ left: i * rail.current.clientWidth, behavior: "smooth" });
  const fleche = "absolute top-1/2 -translate-y-1/2 w-9 h-9 rounded-full bg-white/90 text-dark shadow flex items-center justify-center opacity-0 group-hover:opacity-100 focus-visible:opacity-100 transition-opacity";
  return (
    <div className="relative w-full h-full group">
      <div ref={rail} className="flex w-full h-full overflow-x-auto snap-x snap-mandatory scrollbar-hide"
        onScroll={(e) => setIndex(Math.round(e.currentTarget.scrollLeft / e.currentTarget.clientWidth))}>
        {photos.map((src, i) => (
          // eslint-disable-next-line @next/next/no-img-element
          <img key={src} src={src} alt={photos.length > 1 ? t("photoNumero", { nom, numero: i + 1, total: photos.length }) : ""}
            loading={i ? "lazy" : undefined} className="w-full h-full flex-shrink-0 object-cover snap-center" />
        ))}
      </div>
      {photos.length > 1 && (
        <>
          {index > 0 && <button type="button" onClick={() => aller(index - 1)} aria-label={t("photoPrecedente")} className={cn(fleche, "left-2")}><ChevronLeft size={18} aria-hidden /></button>}
          {index < photos.length - 1 && <button type="button" onClick={() => aller(index + 1)} aria-label={t("photoSuivante")} className={cn(fleche, "right-2")}><ChevronRight size={18} aria-hidden /></button>}
          <div className="absolute bottom-2 inset-x-0 flex justify-center gap-1.5" aria-hidden>
            {photos.map((src, i) => <span key={src} className={cn("w-1.5 h-1.5 rounded-full transition-colors", i === index ? "bg-white" : "bg-white/50")} />)}
          </div>
        </>
      )}
    </div>
  );
}

function CarteVehicule({ c, formule, prixChauffeur, onChoisir }: {
  c: CategorieVehicule; formule: Formule; prixChauffeur: number; onChoisir: () => void;
}) {
  const t = useTranslations("location");
  const propose = formule === "avec_chauffeur" ? c.formules.avec_chauffeur : c.formules.sans_chauffeur;
  return (
    <article className="bg-white rounded-3xl border border-gray-100 shadow-sm overflow-hidden flex flex-col">
      <div className="h-40 bg-gray-50 flex items-center justify-center relative">
        <Galerie photos={c.photos?.length ? c.photos : c.image ? [c.image] : []} nom={c.nom} />
        {formule === "sans_chauffeur" && c.caution === 0 && (
          <span className="absolute top-3 left-3 bg-secondary text-white text-xs font-bold px-2.5 py-1 rounded-full">{t("sansCaution")}</span>
        )}
      </div>
      <div className="p-5 flex flex-col flex-1">
        <p className="text-xs font-bold uppercase tracking-wide text-primary">{t(`gammes.${c.gamme}`)}</p>
        <h2 className="font-heading font-bold text-dark text-lg mt-1">{c.nom}</h2>
        {c.exemple_modele && <p className="text-sm text-gray-500">{c.exemple_modele}{c.annee ? ` · ${c.annee}` : ""}</p>}
        <ul className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-gray-600 mt-3">
          <li className="flex items-center gap-1.5"><Users size={15} /> {t("places", { nombre: c.places })}</li>
          <li className="flex items-center gap-1.5"><Briefcase size={15} /> {t("bagages", { nombre: c.bagages })}</li>
          <li>{t(`boites.${c.boite}`)}</li>
          <li className="flex items-center gap-1.5"><Fuel size={15} /> {t(`carburants.${c.carburant}`)}</li>
          {c.climatisation && <li className="flex items-center gap-1.5"><Snowflake size={15} /> {t("clim")}</li>}
        </ul>
        {formule === "sans_chauffeur" && c.caution > 0 && <p className="text-xs text-gray-500 mt-2">{t("cautionMontant", { montant: formatPrice(c.caution) })}</p>}
        <div className="flex items-end justify-between gap-3 mt-auto pt-4">
          {propose ? (
            <div>
              <p className="font-heading font-bold text-dark text-xl">{formatPrice(c.prix_jour)}<span className="text-xs font-normal text-gray-500">{t("parJour")}</span></p>
              {formule === "avec_chauffeur" && <p className="text-xs text-gray-500">{t("plusChauffeur", { prix: formatPrice(prixChauffeur) })}</p>}
            </div>
          ) : (
            <p className="text-sm text-gray-400">{t("nonProposee")}</p>
          )}
          <button onClick={onChoisir} disabled={!propose}
            className="relative zone-tactile flex items-center gap-1 px-5 py-2.5 rounded-xl bg-primary text-white text-sm font-bold disabled:opacity-40">
            {t("choisir")} <ChevronRight size={16} />
          </button>
        </div>
      </div>
    </article>
  );
}

function FormulaireLocation({ catalogue, categorie, formule, onChanger }: {
  catalogue: CatalogueLocation; categorie: CategorieVehicule | null; formule: Formule; onChanger: () => void;
}) {
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
    queryFn: async () => (await api.get<MonChauffeur[]>("/v1/locations/mes-chauffeurs/")).data,
    enabled: status === "authenticated" && avecChauffeur,
  });
  const sejours = useQuery({
    queryKey: ["reservations", "a-venir"],
    queryFn: async () => (await api.get<{ results: Reservation[] }>("/v1/reservations/")).data.results
      .filter((r) => r.status === "confirmed" && r.check_in > isoDate()),
    enabled: status === "authenticated",
  });

  const devis = useQuery({
    queryKey: ["location", "devis", categorie?.id, formule, lieuPrise, lieuRetour, debut, fin, horsLome, horsPays],
    queryFn: async () => (await api.get<DevisLocation>("/v1/locations/devis/", {
      params: { categorie: categorie?.id, formule, lieu_prise: lieuPrise, lieu_retour: lieuRetour, debut, fin,
                jours_hors_lome: horsLome, jours_hors_pays: horsPays },
    })).data,
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
      const res = await api.post<Location>("/v1/locations/", {
        categorie: categorie?.id ?? null, formule, lieu_prise: Number(lieuPrise), lieu_retour: Number(lieuRetour),
        adresse_prise: adressePrise, adresse_retour: adresseRetour, debut, fin, passagers, telephone, precisions,
        conducteur, permis_numero: permisNumero, permis_pays: permisPays,
        jours_hors_lome: avecChauffeur ? horsLome : 0, jours_hors_pays: avecChauffeur ? horsPays : 0,
        chauffeur_demande: chauffeurDemande ? Number(chauffeurDemande) : null, reservation: sejour || null,
      });
      router.push(`/location/${res.data.id}`);
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

function MesLocations() {
  const t = useTranslations("location");
  const { status } = useSession();
  const { data } = useQuery({
    queryKey: ["locations"],
    queryFn: async () => (await api.get<{ results: Location[] }>("/v1/locations/")).data.results,
    enabled: status === "authenticated",
  });
  if (!data?.length) return null;
  return (
    <section className="mt-12">
      <h2 className="font-heading font-bold text-dark text-xl mb-4">{t("mesLocations")}</h2>
      <ul className="space-y-3">
        {data.map((l) => (
          <li key={l.id}>
            <Link href={`/location/${l.id}`} className="flex items-center justify-between gap-3 bg-white rounded-2xl border border-gray-100 p-4 hover:border-primary/30">
              <span className="min-w-0">
                <span className="block font-semibold text-dark truncate">{l.libelle} · {l.lieu_prise_detail.ville}</span>
                <span className="block text-sm text-gray-500">{formatDate(l.debut_locale)} → {formatDate(l.fin_locale)} · <span className="font-mono text-xs">{l.reference}</span></span>
              </span>
              <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-gray-100 text-dark whitespace-nowrap">{t(`statuts.${l.statut}`)}</span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}

/** Car and driver hire: partner owners' vehicles, filters, detailed request, online payment. */
export default function LocationPage() {
  const t = useTranslations("location");
  const tNav = useTranslations("nav");
  const [formule, setFormule] = useState<Formule>("avec_chauffeur");
  const [gamme, setGamme] = useState<string | null>(null);
  const [boite, setBoite] = useState<string | null>(null);
  const [placesMin, setPlacesMin] = useState<number | null>(null);
  const [choix, setChoix] = useState<CategorieVehicule | null>(null);
  const sansChauffeur = useModule("location_sans_chauffeur");
  const formules = FORMULES.filter((f) => f !== "sans_chauffeur" || sansChauffeur);

  const { data: catalogue, isLoading } = useQuery({
    queryKey: ["location", "catalogue"],
    queryFn: async () => (await api.get<CatalogueLocation>("/v1/locations/catalogue/")).data,
  });

  const categories = useMemo(() => catalogue?.categories ?? [], [catalogue]);
  const gammes = (catalogue?.filtres?.gammes ?? []).filter((g) => categories.some((c) => c.gamme === g.code));
  const paliersPlaces = [5, 7, 9].filter((n) => categories.some((c) => c.places >= n));
  const visibles = categories.filter((c) =>
    (!gamme || c.gamme === gamme) && (!boite || c.boite === boite) && (!placesMin || c.places >= placesMin));

  return (
    <div className="bg-light min-h-[70vh]">
      <PageHero surtitre={<><Car size={16} /> {tNav("location")}</>} titre={t("titre")} sousTitre={t(sansChauffeur ? "sousTitreSansChauffeur" : "sousTitre")} />
      <div className="max-w-6xl mx-auto px-4 sm:px-6 pb-12">

        {isLoading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5 mt-8">{[0, 1, 2].map((i) => <div key={i} className="h-80 skeleton rounded-3xl" />)}</div>
        ) : !catalogue?.active ? (
          <div className="bg-white rounded-3xl border border-gray-100 p-10 text-center mt-8">
            <Car size={40} className="mx-auto text-primary" aria-hidden />
            <p className="font-heading font-bold text-dark text-xl mt-4">{t("bientot")}</p>
            <p className="text-gray-600 mt-2">{t("bientotAide")}</p>
            <Link href="/transfert" className="inline-block mt-5 px-6 py-3 rounded-xl bg-primary text-white font-bold">{tNav("transfertAeroport")}</Link>
          </div>
        ) : choix ? (
          <div className="mt-8">
            <FormulaireLocation catalogue={catalogue} categorie={choix} formule={formule} onChanger={() => setChoix(null)} />
          </div>
        ) : (
          <>
            <div className="mt-8 space-y-4">
              <div className="inline-flex flex-wrap bg-white border border-gray-200 rounded-3xl sm:rounded-full p-1" role="group" aria-label={t("formule")}>
                {formules.map((f) => (
                  <button key={f} type="button" aria-pressed={formule === f} onClick={() => setFormule(f)}
                    className={cn("relative zone-tactile px-5 py-2 rounded-full text-sm font-bold transition-colors", formule === f ? "bg-primary text-white" : "text-dark")}>
                    {t(`formules.${f}`)}
                  </button>
                ))}
              </div>
              <ul className="flex flex-wrap gap-x-5 gap-y-1 text-sm text-gray-600">
                <li className="flex items-center gap-1.5"><BadgeCheck size={15} className="text-secondary" /> {t("argumentVerifie")}</li>
                <li className="flex items-center gap-1.5"><BadgeCheck size={15} className="text-secondary" /> {t("argumentSansFrais")}</li>
                {formule !== "sans_chauffeur" && <li className="flex items-center gap-1.5"><UserRound size={15} className="text-secondary" /> {t("argumentChauffeur", { prix: formatPrice(catalogue.chauffeur?.prix_jour ?? 7000) })}</li>}
              </ul>
              {formule !== "chauffeur_seul" && (
                <>
                  <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
                    <Puce actif={!gamme} onClick={() => setGamme(null)}>{t("tous")}</Puce>
                    {gammes.map((g) => <Puce key={g.code} actif={gamme === g.code} onClick={() => setGamme(g.code)}>{t(`gammes.${g.code}`)}</Puce>)}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {(["automatique", "manuelle"] as const).filter((b) => categories.some((c) => c.boite === b)).map((b) => (
                      <Puce key={b} actif={boite === b} onClick={() => setBoite(boite === b ? null : b)}>{t(`boites.${b}`)}</Puce>
                    ))}
                    {paliersPlaces.map((n) => (
                      <Puce key={n} actif={placesMin === n} onClick={() => setPlacesMin(placesMin === n ? null : n)}>{t("placesMin", { nombre: n })}</Puce>
                    ))}
                  </div>
                </>
              )}
            </div>

            {formule === "chauffeur_seul" ? (
              <div className="mt-6">
                <FormulaireLocation catalogue={catalogue} categorie={null} formule="chauffeur_seul" onChanger={() => setFormule("avec_chauffeur")} />
              </div>
            ) : visibles.length === 0 ? (
              <p className="bg-white rounded-3xl border border-gray-100 p-10 text-center text-gray-500 mt-6">{t("aucun")}</p>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5 mt-6">
                {visibles.map((c) => (
                  <CarteVehicule key={c.id} c={c} formule={formule} prixChauffeur={catalogue.chauffeur?.prix_jour ?? 7000}
                    onChoisir={() => { setChoix(c); window.scrollTo({ top: 0, behavior: "smooth" }); }} />
                ))}
              </div>
            )}
          </>
        )}

        <MesLocations />
      </div>
    </div>
  );
}
