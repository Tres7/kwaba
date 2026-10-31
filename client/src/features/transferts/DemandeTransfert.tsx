"use client";

import { calculerDevis, creerTransfert, lireReservationLiee, listerAeroports } from "./api";
import { clesTransferts } from "./hooks";
import { Link, usePathname, useRouter } from "@/i18n/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useSession } from "next-auth/react";
import { useQuery } from "@tanstack/react-query";
import { Car, Clock, CreditCard, Lock, Luggage, Plane, ShieldCheck, Smartphone, Users, Wallet } from "lucide-react";
import { apiErrorMessage } from "@/lib/api";
import { enEuros, payerTransfert, useConfigPaiement } from "@/lib/paiement";
import { cn, isoDate } from "@/lib/utils";
import Select from "@/components/ui/Select";
import Stepper from "@/components/ui/Stepper";
import FormField from "@/components/ui/FormField";
import { MontantDebite } from "@/components/layout/Devise";
import type { MoyenPaiement } from "@/types/api/paiement";
import type { CategorieVehicule } from "./types";
import { useTranslations } from "next-intl";
import PageHero from "@/components/layout/PageHero";
import { useFormat } from "@/lib/format";

const MOYENS: { id: MoyenPaiement; label: string; icon: typeof Smartphone }[] = [
  { id: "mobile_money", label: "mobileMoney", icon: Smartphone },
  { id: "carte", label: "carte", icon: CreditCard },
  { id: "paypal", label: "paypal", icon: Wallet },
];

const CATEGORIES: CategorieVehicule[] = ["berline", "confort", "van"];
// Input kept while signing in (session storage, cleared when the tab is closed)
const BROUILLON = "kwaba_transfert_brouillon";
// The draft holds a phone number: a tab left open does not keep it for long
const DUREE_BROUILLON_MS = 30 * 60 * 1000;

const champ = "w-full py-3 px-4 bg-white border border-gray-200 rounded-xl text-base sm:text-sm text-dark focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary";

function TransfertContent() {
  const { formatFcfa, formatPrice } = useFormat();
  const t = useTranslations("transfert");
  const tRes = useTranslations("reservation");
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const reservationId = searchParams.get("reservation");
  const { data: session, status } = useSession();
  const connecte = status === "authenticated" && !!session && !session.error;
  const { data: config } = useConfigPaiement();

  // Prefilled from a link (Concierge: ?aeroport=LFW&date=…&heure=…&passagers=…&bagages=…)
  const nombre = (cle: string, defaut: number, max: number) => Math.min(max, Math.max(0, Number(searchParams.get(cle)) || defaut));
  const [aeroport, setAeroport] = useState(searchParams.get("aeroport")?.toUpperCase() ?? "");
  const [date, setDate] = useState(searchParams.get("date") ?? "");
  const [heure, setHeure] = useState(searchParams.get("heure") ?? "");
  const [vol, setVol] = useState("");
  const [passagers, setPassagers] = useState(Math.max(1, nombre("passagers", 1, 7)));
  const [bagages, setBagages] = useState(nombre("bagages", 1, 10));
  const [categorie, setCategorie] = useState<CategorieVehicule | null>(null);
  const [destination, setDestination] = useState("");
  const [telephone, setTelephone] = useState("");
  const [message, setMessage] = useState("");
  const [moyen, setMoyen] = useState<MoyenPaiement | null>(null);
  const [erreurs, setErreurs] = useState<Record<string, string>>({});
  const [envoi, setEnvoi] = useState(false);

  // Back from the sign-in page: the request resumes where the traveller left it
  useEffect(() => {
    try {
      const brouillon = sessionStorage.getItem(BROUILLON);
      if (!brouillon) return;
      sessionStorage.removeItem(BROUILLON);
      const b = JSON.parse(brouillon);
      if (!(Date.now() - b.enregistreLe < DUREE_BROUILLON_MS)) return;
      setAeroport(b.aeroport ?? ""); setDate(b.date ?? ""); setHeure(b.heure ?? ""); setVol(b.vol ?? "");
      setPassagers(b.passagers ?? 1); setBagages(b.bagages ?? 1); setCategorie(b.categorie ?? null);
      setDestination(b.destination ?? ""); setTelephone(b.telephone ?? ""); setMessage(b.message ?? "");
    } catch { /* storage unavailable or unreadable draft: empty form */ }
  }, []);

  const { data: aeroports = [] } = useQuery({
    queryKey: [...clesTransferts.tous, "aeroports"],
    queryFn: listerAeroports,
    staleTime: 60 * 60 * 1000,
  });

  // Related Kwa-Ba stay: the airport, date, travellers and address are prefilled
  const { data: reservation } = useQuery({
    queryKey: ["reservation", reservationId],
    queryFn: () => lireReservationLiee(reservationId as string),
    enabled: !!reservationId && connecte,
    retry: false,
  });

  useEffect(() => {
    if (!reservation) return;
    const h = reservation.hebergement_detail;
    setDate((d) => d || reservation.check_in);
    setPassagers(Math.min(7, reservation.guests_count));
    setDestination((d) => d || [h.name, h.location, h.city].filter(Boolean).join(", "));
    const ville = h.city.toLowerCase();
    const proche = aeroports.find((a) => ville.includes(a.ville.toLowerCase()) || a.ville.toLowerCase().includes(ville));
    if (proche) setAeroport((a) => a || proche.code);
  }, [reservation, aeroports]);

  const arrivee = date && heure ? `${date}T${heure}` : "";
  const { data: devis, isFetching: calcul } = useQuery({
    queryKey: [...clesTransferts.tous, "devis", aeroport, arrivee, passagers, bagages],
    queryFn: () => calculerDevis({ aeroport, arrivee, passagers, bagages }),
    enabled: !!aeroport && !!arrivee,
    placeholderData: (precedent) => precedent,
  });

  const options = useMemo(() => devis?.options ?? [], [devis]);
  // Chosen vehicle, otherwise the cheapest suitable one
  const choix = options.find((o) => o.categorie === categorie && o.disponible) ?? options.find((o) => o.disponible);
  const moyensDispo = MOYENS.filter((m) => config?.moyens.includes(m.id));
  const moyenChoisi = moyen && moyensDispo.some((m) => m.id === moyen) ? moyen : moyensDispo[0]?.id;
  const enLigne = !!config?.actif;
  // "From" price of each vehicle, shown before any choice: those of the chosen airport, otherwise the lowest ones
  const prixAPartir = (c: CategorieVehicule) => {
    const liste = (aeroport ? aeroports.filter((a) => a.code === aeroport) : aeroports).map((a) => a.prix?.[c]).filter((p): p is number => !!p);
    return liste.length ? Math.min(...liste) : null;
  };
  const complet = !!choix && !!vol && !!destination && !!telephone && !devis?.trop_tard;

  const reserver = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!connecte) {
      // The whole request is filled in without an account; sign-in is only asked here, just before payment
      try {
        sessionStorage.setItem(BROUILLON, JSON.stringify({ enregistreLe: Date.now(), aeroport, date, heure, vol, passagers, bagages, categorie: choix?.categorie ?? categorie, destination, telephone, message }));
      } catch { /* without storage, the traveller types it again after signing in */ }
      router.push(`/login?callbackUrl=${encodeURIComponent(`${pathname}?${searchParams.toString()}`)}`);
      return;
    }
    if (!choix) return;
    setEnvoi(true);
    setErreurs({});
    try {
      const transfert = await creerTransfert({
        aeroport, arrivee, numero_vol: vol, passagers, bagages, categorie: choix.categorie,
        destination, telephone, message, reservation: reservation?.id ?? null,
      });
      if (transfert.statut === "en_attente_paiement" && moyenChoisi) {
        try {
          await payerTransfert(transfert.id, moyenChoisi);
          return;
        } catch {
          // The payment did not start: the transfer page allows trying again
        }
      }
      router.push(`/transfert/${transfert.id}`);
    } catch (err) {
      const data = (err as { response?: { data?: Record<string, string[] | string> } }).response?.data;
      if (data && typeof data === "object" && !("detail" in data)) {
        setErreurs(Object.fromEntries(Object.entries(data).map(([k, v]) => [k, Array.isArray(v) ? v[0] : String(v)])));
      } else {
        setErreurs({ general: apiErrorMessage(err, t("erreurReservation")) });
      }
      setEnvoi(false);
    }
  };

  const etiquette = "block text-xs font-bold text-dark uppercase tracking-wide mb-2";

  return (
    <div className="bg-light pb-12">
      <PageHero surtitre={<><Plane size={16} /> {t("surtitre")}</>} titre={t("titre")} sousTitre={t("sousTitre")}>
        <ul className="flex flex-wrap gap-x-6 gap-y-2 mt-6 text-sm text-white/90">
          <li className="flex items-center gap-2"><Clock size={15} /> {t("attenteIncluse", { minutes: devis?.attente_incluse_minutes ?? 60 })}</li>
          <li className="flex items-center gap-2"><ShieldCheck size={15} /> {t("annulationGratuite")}</li>
          <li className="flex items-center gap-2"><Lock size={15} /> {t("aucunPrixNegocie")}</li>
        </ul>
      </PageHero>

      <form method="post" onSubmit={reserver} noValidate className="max-w-6xl mx-auto px-4 sm:px-6 py-8 grid grid-cols-1 lg:grid-cols-5 gap-6 lg:gap-10">
        <div className="lg:col-span-3 space-y-6">
          <section className="bg-white rounded-3xl border border-gray-100 shadow-sm p-5 sm:p-8 space-y-5">
            <h2 className="font-heading font-bold text-dark text-xl">{t("votreVol")}</h2>
            {reservation && (
              <p className="text-sm text-dark bg-primary/5 rounded-xl px-4 py-3">
                {t.rich("prerempli", { nom: reservation.hebergement_detail.name, strong: (x) => <strong>{x}</strong> })}
              </p>
            )}
            <div>
              <p className={etiquette}>{t("aeroport")}</p>
              <Select label={t("aeroport")} value={aeroport} onChange={setAeroport}
                options={aeroports.map((a) => ({ value: a.code, label: `${a.ville} (${a.code})`, hint: a.nom }))} />
              {erreurs.aeroport && <p className="text-xs text-red-600 mt-1.5 ml-1">{erreurs.aeroport}</p>}
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label htmlFor="t-date" className={etiquette}>{t("dateArrivee")}</label>
                <input id="t-date" type="date" min={isoDate()} value={date} onChange={(e) => setDate(e.target.value)} className={champ} required />
              </div>
              <div>
                <label htmlFor="t-heure" className={etiquette}>{t("heureAtterrissage")}</label>
                <input id="t-heure" type="time" value={heure} onChange={(e) => setHeure(e.target.value)} className={champ} aria-describedby="t-heure-aide" required />
                <p id="t-heure-aide" className="text-xs text-gray-600 mt-1.5 ml-1">{t("heureLocale")}</p>
              </div>
              <FormField label={t("numeroVol")} id="t-vol" value={vol} onChange={(e) => setVol(e.target.value.toUpperCase())}
                placeholder="AF 520" error={erreurs.numero_vol} autoComplete="off" required />
            </div>
            {erreurs.arrivee && <p role="alert" className="text-sm text-red-700">{erreurs.arrivee}</p>}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-4 pt-2">
              <Stepper label={t("passagers")} value={passagers} onChange={setPassagers} min={1} max={7} />
              <Stepper label={t("bagages")} hint={t("bagagesAide")} value={bagages} onChange={setBagages} min={0} max={10} />
            </div>
          </section>

          <section className="bg-white rounded-3xl border border-gray-100 shadow-sm p-5 sm:p-8">
            <h2 className="font-heading font-bold text-dark text-xl">{t("vehicule")}</h2>
            {!aeroport || !arrivee ? (
              <>
                <ul className="space-y-3 mt-4">
                  {CATEGORIES.filter((c) => prixAPartir(c) !== null).map((c) => (
                    <li key={c} className="flex items-center gap-4 rounded-2xl p-4 border border-gray-100">
                      <div className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 bg-gray-100 text-gray-600"><Car size={22} /></div>
                      <div className="flex-1 min-w-0">
                        <p className="font-bold text-sm text-dark">{t(`vehicules.${c}.nom`)}</p>
                        <p className="text-xs text-gray-600">{t(`vehicules.${c}.description`)}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-[11px] text-gray-500">{t("aPartirDe")}</p>
                        <p className="font-heading font-bold text-dark whitespace-nowrap">{formatPrice(prixAPartir(c)!)}</p>
                      </div>
                    </li>
                  ))}
                </ul>
                <p className="text-sm text-gray-600 mt-3">{t("choisirPourPrix")}</p>
              </>
            ) : devis?.trop_tard ? (
              <p role="alert" className="text-sm text-red-700 bg-red-50 rounded-xl p-3 mt-3">
                {t("tropTard", { heures: devis.delai_min_heures })}
              </p>
            ) : (
              <div className={cn("space-y-3 mt-4", calcul && "opacity-60")} role="radiogroup" aria-label={t("vehicule")} aria-busy={calcul}>
                {options.map((o) => {
                  const actif = choix?.categorie === o.categorie;
                  return (
                    <button
                      key={o.categorie} type="button" role="radio" aria-checked={actif} disabled={!o.disponible}
                      onClick={() => setCategorie(o.categorie)}
                      className={cn("w-full flex items-center gap-4 rounded-2xl p-4 border text-left transition-all disabled:opacity-50 disabled:cursor-not-allowed",
                        actif ? "border-primary bg-primary/5 shadow-sm" : "border-gray-100 hover:border-primary/30")}
                    >
                      <div className={cn("w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0", actif ? "bg-primary text-white" : "bg-gray-100 text-gray-600")}>
                        <Car size={22} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className={cn("font-bold text-sm", actif ? "text-primary" : "text-dark")}>{t(`vehicules.${o.categorie}.nom`)}</p>
                        <p className="text-xs text-gray-600">{t(`vehicules.${o.categorie}.description`)}</p>
                        <p className="flex items-center gap-3 text-xs text-gray-600 mt-1">
                          <span className="flex items-center gap-1"><Users size={12} /> {o.passagers}</span>
                          <span className="flex items-center gap-1"><Luggage size={12} /> {o.bagages}</span>
                          {!o.disponible && <span className="text-red-700 font-semibold">{passagers > o.passagers ? t("maxPassagers", { nombre: o.passagers }) : t("maxBagages", { nombre: o.bagages })}</span>}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="font-heading font-bold text-dark whitespace-nowrap">{formatPrice(o.prix)}</p>
                      </div>
                    </button>
                  );
                })}
                {options.length > 0 && !choix && <p className="text-sm text-red-700">{t("aucunVehicule")}</p>}
              </div>
            )}
          </section>

          <section className="bg-white rounded-3xl border border-gray-100 shadow-sm p-5 sm:p-8 space-y-4">
            <h2 className="font-heading font-bold text-dark text-xl">{t("destinationContact")}</h2>
            <FormField label={t("adresseDestination")} id="t-destination" value={destination} onChange={(e) => setDestination(e.target.value)}
              placeholder={t("adressePlaceholder")} error={erreurs.destination} required />
            <FormField label={t("telephone")} id="t-telephone" type="tel" autoComplete="tel" value={telephone}
              onChange={(e) => setTelephone(e.target.value)} placeholder="+33 6 12 34 56 78" error={erreurs.telephone}
              hint={t("telephoneAide")} required />
            <div>
              <label htmlFor="t-message" className={etiquette}>{t("messageChauffeur")} <span className="normal-case font-normal text-gray-600">({t("facultatif")})</span></label>
              <textarea id="t-message" rows={2} maxLength={500} value={message} onChange={(e) => setMessage(e.target.value)}
                placeholder={t("messagePlaceholder")} className={cn(champ, "resize-none")} />
            </div>
          </section>
        </div>

        <aside className="lg:col-span-2">
          <div className="bg-white rounded-3xl shadow-card border border-gray-100 p-5 sm:p-6 lg:sticky lg:top-28 space-y-5">
            <h2 className="font-heading font-bold text-dark text-lg">{t("recapitulatif")}</h2>
            {choix ? (
              <dl className="text-sm space-y-2">
                <div className="flex justify-between gap-3"><dt className="text-gray-600">{t("vehicule")}</dt><dd className="font-medium text-dark">{t(`vehicules.${choix.categorie}.nom`)}</dd></div>
                <div className="flex justify-between gap-3"><dt className="text-gray-600">{t("passagersBagages")}</dt><dd className="font-medium text-dark">{passagers} · {bagages}</dd></div>
                <div className="flex justify-between items-center gap-3 pt-3 border-t border-gray-100">
                  <dt className="font-heading font-bold text-dark text-base">{t("total")}</dt>
                  <dd className="text-right"><span className="block font-heading font-bold text-primary text-2xl">{formatPrice(choix.prix)}</span><MontantDebite montant={choix.prix} /></dd>
                </div>
              </dl>
            ) : (
              <p className="text-sm text-gray-600">{t("prixApres")}</p>
            )}

            {enLigne && moyensDispo.length > 0 && (
              <fieldset>
                <legend className={etiquette}>{t("payerAvec")}</legend>
                <div className="grid grid-cols-3 gap-2">
                  {moyensDispo.map(({ id, label, icon: Icon }) => (
                    <button key={id} type="button" aria-pressed={moyenChoisi === id} onClick={() => setMoyen(id)}
                      className={cn("flex flex-col items-center gap-1.5 rounded-2xl border p-3 text-xs font-bold transition-colors",
                        moyenChoisi === id ? "border-primary bg-primary/5 text-primary" : "border-gray-200 text-dark hover:border-primary/40")}>
                      <Icon size={18} /> {tRes(`moyens.${label}`)}
                    </button>
                  ))}
                </div>
              </fieldset>
            )}

            {erreurs.general && <p role="alert" className="text-sm text-red-700 bg-red-50 rounded-xl p-3">{erreurs.general}</p>}

            <button type="submit" disabled={envoi || !complet}
              className="w-full bg-secondary hover:bg-secondary-600 text-white font-bold py-4 rounded-2xl shadow-md disabled:opacity-60">
              {!connecte
                ? t("seConnecterPourPayer")
                : envoi
                  ? t("redirection")
                  : choix
                    ? enLigne ? tRes("payer", { montant: moyenChoisi === "paypal" && config ? enEuros(choix.prix, config.fcfa_par_euro) : formatFcfa(choix.prix) }) : t("reserver")
                    : t("reserver")}
            </button>
            {!connecte && <p className="text-xs text-gray-600 text-center leading-relaxed">{t("connexionDerniere")}</p>}
            <p className="text-xs text-gray-600 text-center leading-relaxed">
              {t.rich("infoChauffeur", { cgu: (x) => <Link href="/cgv" className="text-primary font-medium">{x}</Link> })}
            </p>
          </div>
        </aside>
      </form>
    </div>
  );
}

export default function TransfertPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-light" />}>
      <TransfertContent />
    </Suspense>
  );
}
