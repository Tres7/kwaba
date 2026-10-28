"use client";

import { Link, useRouter } from "@/i18n/navigation";
import { useState, Suspense } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { useSession } from "next-auth/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Check, Info, Smartphone, CreditCard, Wallet, MapPin, Lock } from "lucide-react";
import api, { apiErrorMessage } from "@/lib/api";
import { allerPayer, enEuros, useConfigPaiement, useOperateursMobileMoney } from "@/lib/paiement";
import RatingBadge from "@/components/avis/RatingBadge";
import { MontantDebite } from "@/components/layout/Devise";
import PolitiqueAnnulation from "@/components/hebergement/PolitiqueAnnulation";
import { calculateNights, calculateServiceFee, cn, FALLBACK_IMAGE, formatDate, formatFcfa, formatPrice, isoDate, SERVICE_FEE_RATE } from "@/lib/utils";
import type { Hebergement, Reservation } from "@/types/api/models";
import { useTranslations } from "next-intl";

const PAYMENT_METHODS = [
  { id: "mobile_money", label: "mobileMoney", sublabel: "operateurs", icon: Smartphone },
  { id: "carte", label: "carte", sublabel: "Visa, Mastercard", icon: CreditCard },
  { id: "paypal", label: "paypal", sublabel: "paypalDetail", icon: Wallet },
] as const;

function ReservationContent() {
  const t = useTranslations("reservation");
  const tFiche = useTranslations("fiche");
  const tVoy = useTranslations("voyageurs");
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const { data: session } = useSession();

  const checkIn = searchParams.get("check_in") || "";
  const checkOut = searchParams.get("check_out") || "";
  const guestsCount = Math.max(1, parseInt(searchParams.get("guests") || "1", 10) || 1);
  // Unit type and number of units chosen on the listing page (the establishment's first type, 1 unit otherwise)
  const typeDemande = searchParams.get("type") || "";
  const unitesDemandees = Math.max(1, parseInt(searchParams.get("unites") || "1", 10) || 1);

  const [paymentMethod, setPaymentMethod] = useState<(typeof PAYMENT_METHODS)[number]["id"]>("mobile_money");
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [accepte, setAccepte] = useState(false);

  const { data: config } = useConfigPaiement();
  const operateurs = useOperateursMobileMoney();
  const enLigne = !!config?.actif;
  const moyens = PAYMENT_METHODS.filter((m) => !enLigne || config?.moyens.includes(m.id));
  const moyenChoisi = moyens.some((m) => m.id === paymentMethod) ? paymentMethod : moyens[0]?.id ?? "mobile_money";

  const { data: hebergement, isLoading, isError } = useQuery({
    queryKey: ["hebergement", params.id, "reservation"],
    queryFn: async () => (await api.get<Hebergement>(`/v1/hebergements/${params.id}/`)).data,
    retry: false,
  });

  if (isLoading) {
    return <div className="max-w-6xl mx-auto px-4 sm:px-6 py-10"><div className="h-96 skeleton rounded-3xl" /></div>;
  }

  if (isError || !hebergement) {
    return (
      <div className="min-h-[50vh] flex flex-col items-center justify-center gap-3 text-center px-6">
        <p className="font-heading font-bold text-xl text-dark">{t("introuvable")}</p>
        <Link href="/recherche" className="text-primary font-bold hover:underline">{t("retourRecherche")}</Link>
      </div>
    );
  }

  const nights = calculateNights(checkIn, checkOut);
  const datesInvalid = !checkIn || !checkOut || nights <= 0 || checkIn < isoDate();
  const typeLogement = hebergement.types?.find((u) => u.id === typeDemande) ?? hebergement.types?.[0];
  const nbUnites = Math.min(unitesDemandees, typeLogement?.quantite ?? 1);
  const prixUnite = Number(typeLogement?.prix_nuit ?? hebergement.price_per_night);
  const subtotal = prixUnite * nbUnites * nights;
  // Visitor's rate: 6 %, or 3 % if they already stayed with this host (the server applies the same calculation)
  const tauxFrais = hebergement.frais_voyageur ?? SERVICE_FEE_RATE;
  const serviceFee = calculateServiceFee(subtotal, tauxFrais);
  const total = subtotal + serviceFee;
  const backToListing = `/hebergements/${hebergement.id}?check_in=${checkIn}&check_out=${checkOut}&guests=${guestsCount}`
    + (typeLogement ? `&type=${typeLogement.id}&unites=${nbUnites}` : "");

  const handleConfirm = async () => {
    if (datesInvalid || submitting) return;
    setSubmitting(true);
    setError("");
    try {
      const res = await api.post<Reservation>("/v1/reservations/", {
        hebergement: hebergement.id,
        ...(typeLogement ? { type_logement: typeLogement.id, nb_unites: nbUnites } : {}),
        check_in: checkIn,
        check_out: checkOut,
        guests_count: guestsCount,
        payment_method: moyenChoisi,
        message: message.trim(),
        // The server computes the total again and refuses if it changed since this summary was displayed
        total_attendu: total,
      });
      queryClient.invalidateQueries({ queryKey: ["reservations"] });
      if (res.data.status !== "pending") {
        router.push(`/reservation/confirmation/${res.data.id}`);
        return;
      }
      // Dates held: on to the provider's secure payment page
      try {
        await allerPayer(res.data.id, moyenChoisi);
      } catch (err) {
        router.push(`/reservation/paiement/${res.data.id}?erreur=${encodeURIComponent(apiErrorMessage(err, t("paiementNonDemarre")))}`);
      }
    } catch (err) {
      setError(apiErrorMessage(err, t("reservationNonEnregistree")));
      // Price changed in the meantime: the summary is updated with the new total
      queryClient.invalidateQueries({ queryKey: ["hebergement", params.id, "reservation"] });
      setSubmitting(false);
    }
  };

  return (
    <div className="bg-light pb-12">
      <div className="bg-white border-b border-gray-100 px-4 sm:px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center gap-4">
          <button onClick={() => router.back()} className="text-dark hover:text-primary transition-colors" aria-label={t("retour")}>
            <ArrowLeft size={20} />
          </button>
          <h1 className="font-heading font-bold text-dark text-lg sm:text-xl">{t("confirmerPayer")}</h1>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6 sm:py-10">
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 lg:gap-10">
          <div className="lg:col-span-3 space-y-6">
            <section className="bg-white rounded-3xl shadow-sm border border-gray-100 p-5 sm:p-8">
              <div className="flex items-center justify-between mb-5">
                <h2 className="font-heading font-bold text-dark text-xl">{t("votreVoyage")}</h2>
                <Link href={backToListing} className="text-sm font-bold text-primary hover:underline">{t("modifier")}</Link>
              </div>
              {datesInvalid ? (
                <p className="text-sm text-red-700 bg-red-50 rounded-xl p-3">
                  {t("datesInvalides")} <Link href={backToListing} className="font-bold underline">{t("autresDates")}</Link>
                </p>
              ) : (
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="font-bold text-dark">{t("dates")}</p>
                    <p className="text-gray-500 mt-0.5">{formatDate(checkIn)} – {formatDate(checkOut)}</p>
                    <p className="text-gray-500">{tFiche("nuits", { nombre: nights })}</p>
                  </div>
                  <div>
                    <p className="font-bold text-dark">{t("voyageurs")}</p>
                    <p className="text-gray-500 mt-0.5">{tVoy("voyageurs", { nombre: guestsCount })}</p>
                    {typeLogement && (hebergement.types?.length ?? 0) > 1 && <p className="text-gray-500">{typeLogement.nom}</p>}
                    {nbUnites > 1 && <p className="text-gray-500">{tFiche("unitesNombre", { nombre: nbUnites })}</p>}
                  </div>
                </div>
              )}
            </section>

            <section className="bg-white rounded-3xl shadow-sm border border-gray-100 p-5 sm:p-8">
              <h2 className="font-heading font-bold text-dark text-xl mb-4">{t("reservePar")}</h2>
              <p className="text-sm text-dark font-semibold">{session?.user?.name}</p>
              <p className="text-sm text-gray-500">{session?.user?.email}</p>
              <label htmlFor="message" className="block text-xs font-bold text-dark uppercase tracking-wide mb-2 mt-6">
                {t("messageHote")} <span className="normal-case font-normal text-gray-400">({t("optionnel")})</span>
              </label>
              <textarea
                id="message" value={message} onChange={(e) => setMessage(e.target.value)} maxLength={1000}
                placeholder={t("messagePlaceholder")} rows={3}
                className="w-full bg-gray-50 border border-gray-200 rounded-xl py-3 px-4 text-base sm:text-sm text-dark outline-none focus:border-primary/50 transition-colors resize-none"
                aria-describedby="message-info"
              />
              <p id="message-info" className="text-xs text-gray-600 mt-2">
                {t("messageInfo")}
              </p>
            </section>

            <section id="mode-paiement" className="bg-white rounded-3xl shadow-sm border border-gray-100 p-5 sm:p-8 scroll-mt-28">
              <h2 className="font-heading font-bold text-dark text-xl mb-5">{t("modePaiement")}</h2>
              <div className="space-y-3" role="radiogroup" aria-label={t("modePaiement")}>
                {moyens.map((method) => {
                  const Icon = method.icon;
                  const isActive = moyenChoisi === method.id;
                  return (
                    <button
                      key={method.id} type="button" role="radio" aria-checked={isActive}
                      onClick={() => setPaymentMethod(method.id)}
                      className={cn("w-full flex items-center gap-4 rounded-2xl p-4 sm:p-5 border transition-all", isActive ? "border-primary bg-primary/5 shadow-sm" : "border-gray-100 hover:border-primary/30")}
                    >
                      <div className={cn("w-11 h-11 rounded-xl flex items-center justify-center transition-colors flex-shrink-0", isActive ? "bg-primary text-white" : "bg-gray-100 text-gray-500")}>
                        <Icon size={20} />
                      </div>
                      <div className="text-left flex-1 min-w-0">
                        <p className={cn("font-bold text-sm", isActive ? "text-primary" : "text-dark")}>{t(`moyens.${method.label}`)}</p>
                        <p className="text-gray-500 text-xs mt-0.5">
                          {method.sublabel === "paypalDetail" ? t("moyens.paypalDetail") : method.sublabel === "operateurs" ? operateurs : method.sublabel}
                          {method.id === "paypal" && config && !datesInvalid && <> · <strong className="text-dark">{enEuros(total, config.fcfa_par_euro)}</strong></>}
                        </p>
                      </div>
                      <div className={cn("w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0", isActive ? "border-primary bg-primary" : "border-gray-300")}>
                        {isActive && <Check size={10} className="text-white" />}
                      </div>
                    </button>
                  );
                })}
              </div>
              {enLigne ? (
                <p className="flex items-start gap-2 text-xs text-gray-600 mt-4 bg-gray-50 rounded-xl p-3">
                  <Lock size={14} className="flex-shrink-0 mt-0.5 text-secondary" />
                  <span>
                    {t("redirectionInfo", { prestataire: moyenChoisi === "paypal" ? "PayPal" : "FedaPay", minutes: config?.delai_paiement_minutes ?? 30 })}
                  </span>
                </p>
              ) : (
                <p className="flex items-start gap-2 text-xs text-gray-500 mt-4 bg-gray-50 rounded-xl p-3">
                  <Info size={14} className="flex-shrink-0 mt-0.5 text-primary" />
                  {t("paiementInactif")}
                </p>
              )}
            </section>
          </div>

          <div className="lg:col-span-2">
            <div className="bg-white rounded-3xl shadow-card border border-gray-100 p-5 sm:p-6 lg:sticky lg:top-28">
              <div className="flex gap-4 pb-5 border-b border-gray-100">
                <img src={hebergement.image_url || FALLBACK_IMAGE} alt={hebergement.name} className="w-24 h-20 rounded-2xl object-cover flex-shrink-0" />
                <div className="min-w-0">
                  <h3 className="font-bold text-dark text-sm line-clamp-2">{hebergement.name}</h3>
                  <p className="flex items-center gap-1 text-gray-500 text-xs mt-1"><MapPin size={12} className="text-primary flex-shrink-0" /><span className="truncate">{hebergement.city}</span></p>
                  <RatingBadge rating={hebergement.rating} count={hebergement.review_count} className="mt-1" />
                </div>
              </div>

              <div className="py-5 space-y-3 border-b border-gray-100 text-sm">
                <h3 className="font-heading font-bold text-dark text-base mb-2">{t("detailsPrix")}</h3>
                <div className="flex justify-between gap-2">
                  <span className="text-gray-600">
                    {formatPrice(prixUnite)} × {nbUnites > 1 && <>{tFiche("unitesNombre", { nombre: nbUnites })} × </>}{tFiche("nuits", { nombre: nights })}
                  </span>
                  <span className="font-medium text-dark">{formatPrice(subtotal)}</span>
                </div>
                <div className="flex justify-between gap-2">
                  <span className="text-gray-600">
                    {tFiche("fraisService", { taux: Math.round(tauxFrais * 100) })}
                    {tauxFrais < SERVICE_FEE_RATE && <span className="block text-xs text-secondary font-semibold">{tFiche("clientFidele")}</span>}
                  </span>
                  <span className="font-medium text-dark">{formatPrice(serviceFee)}</span>
                </div>
              </div>

              <div className="pt-5 flex justify-between items-center mb-5">
                <span className="font-heading font-bold text-dark text-lg">{tFiche("total")}</span>
                <span className="text-right"><span className="block font-heading font-bold text-primary text-2xl">{formatPrice(total)}</span><MontantDebite montant={total} /></span>
              </div>

              {error && <p role="alert" className="text-sm text-red-700 bg-red-50 border border-red-100 rounded-xl p-3 mb-4">{error}</p>}

              {enLigne && (
                <p className="flex items-center justify-between gap-2 text-sm text-gray-600 mb-3">
                  <span>{t("payerAvec")} <strong className="text-dark">{t(`moyens.${moyens.find((m) => m.id === moyenChoisi)?.label ?? "mobileMoney"}`)}</strong></span>
                  <a href="#mode-paiement" className="text-primary font-semibold hover:underline">{t("changer")}</a>
                </p>
              )}
              <div className="mb-4">
                <PolitiqueAnnulation politique={hebergement.politique_annulation ?? "moderee"} compact />
              </div>

              {/* Express acceptance of the terms of sale, the listing rules and the cancellation policy (terms of sale, art. 5.2) */}
              <label className="flex items-start gap-2.5 text-xs text-gray-600 leading-relaxed mb-4 cursor-pointer">
                <input type="checkbox" checked={accepte} onChange={(e) => setAccepte(e.target.checked)}
                  className="mt-0.5 h-4 w-4 flex-shrink-0 rounded border-gray-300 text-primary focus:ring-primary" />
                <span>
                  {t.rich(enLigne ? "accepterPaiement" : "accepterConfirmation", {
                    cgu: (x) => <Link href="/cgv" className="text-primary font-medium">{x}</Link>,
                    annulation: (x) => <Link href="/remboursement" className="text-primary font-medium">{x}</Link>,
                  })}
                </span>
              </label>

              <button onClick={handleConfirm} disabled={submitting || datesInvalid || !accepte} className="w-full bg-secondary hover:bg-secondary-600 text-white font-bold py-4 rounded-2xl shadow-md transition-all text-base disabled:opacity-60">
                {submitting
                  ? enLigne ? t("redirection") : t("traitement")
                  : enLigne ? t("payer", { montant: moyenChoisi === "paypal" && config ? enEuros(total, config.fcfa_par_euro) : formatFcfa(total) }) : t("confirmerReservation")}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function ReservationPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-light" />}>
      <ReservationContent />
    </Suspense>
  );
}
