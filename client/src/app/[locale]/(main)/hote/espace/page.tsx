"use client";

import { Link, useRouter } from "@/i18n/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useSession } from "next-auth/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Pencil, Trash2, Eye, EyeOff, BedDouble, Calendar, CalendarDays, Users, MapPin, MessageCircle, ShieldCheck, Clock, AlertTriangle, Hourglass } from "lucide-react";
import { toast } from "sonner";
import api, { apiErrorMessage } from "@/lib/api";
import { cn, FALLBACK_IMAGE, formatDate, formatPrice, isoDate, TYPE_LABELS } from "@/lib/utils";
import HebergementForm from "@/components/hote/HebergementForm";
import RatingBadge from "@/components/avis/RatingBadge";
import RevenusHote from "@/components/hote/RevenusHote";
import CandidatureHote from "@/components/hote/CandidatureHote";
import PreinscriptionHote from "@/components/hote/PreinscriptionHote";
import FenetreOuverture from "@/components/lancement/FenetreOuverture";
import { usePrelancement } from "@/lib/usePrelancement";
import type { Hebergement, Paginated, Reservation } from "@/types/api/models";
import type { MessagingConversation } from "@/types/api/messaging";
import { useTranslations } from "next-intl";

type Tab = "annonces" | "reservations" | "revenus";

// Pre-launch window already shown when the host space opened, for this browsing session
const CLE_FENETRE_VUE = "kwaba_fenetre_ouverture_vue";

const PAYMENT_LABELS: Record<string, string> = { mobile_money: "mobileMoney", carte: "carte", paypal: "paypal" };

function EspaceHoteContent() {
  const t = useTranslations("espaceHote");
  const tVerif = useTranslations("espaceHote.verification");
  const tAnnonce = useTranslations("annonce");
  const tRes = useTranslations("reservation");
  const tPre = useTranslations("prelancement");
  const prelancement = usePrelancement();
  const [fenetre, setFenetre] = useState(false);
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const { data: session, status } = useSession();
  const [tab, setTab] = useState<Tab>("annonces");
  const [editing, setEditing] = useState<Hebergement | "new" | null>(null);
  const [contactId, setContactId] = useState<string | null>(null);

  // Opens (or finds) the conversation with the traveller of this booking
  const contacterVoyageur = async (r: Reservation) => {
    setContactId(r.id);
    try {
      const res = await api.post<MessagingConversation>("/v1/messaging/conversations/avec-voyageur/", { reservation_id: r.id });
      router.push(`/messages/${res.data.id}`);
    } catch (err) {
      toast.error(apiErrorMessage(err, t("erreurConversation")));
      setContactId(null);
    }
  };

  const isHost = session?.user?.role === "hote" || session?.user?.role === "admin";

  // Pre-launch: the window comes before any new listing, and once per session when the host space opens
  const nouvelle = () => (prelancement ? setFenetre(true) : setEditing("new"));
  const fermerFenetre = useCallback(() => setFenetre(false), []);
  const creerDepuisFenetre = () => {
    setFenetre(false);
    setEditing("new");
  };

  useEffect(() => {
    if (!prelancement || !isHost) return;
    try {
      if (window.sessionStorage.getItem(CLE_FENETRE_VUE) === "1") return;
      window.sessionStorage.setItem(CLE_FENETRE_VUE, "1");
    } catch { /* storage unavailable: shown on every visit */ }
    setFenetre(true);
  }, [prelancement, isHost]);

  useEffect(() => {
    const onglet = searchParams.get("onglet");
    if (onglet === "revenus" || onglet === "reservations") setTab(onglet);
  }, [searchParams]);

  useEffect(() => {
    if (searchParams.get("bienvenue") === "1") {
      toast.success(t("bienvenue"));
      router.replace("/hote/espace");
    }
  }, [searchParams, router, t]);

  const { data: annonces = [], isLoading } = useQuery({
    queryKey: ["hebergements", "mine"],
    queryFn: async () => (await api.get<Paginated<Hebergement>>("/v1/hebergements/mine/")).data.results,
    enabled: isHost,
  });

  const { data: reservations = [], isLoading: resLoading } = useQuery({
    queryKey: ["reservations", "host"],
    queryFn: async () => (await api.get<Paginated<Reservation>>("/v1/reservations/", { params: { as: "host" } })).data.results,
    enabled: isHost,
  });

  if (status === "loading") return <div className="max-w-6xl mx-auto px-4 py-10"><div className="h-64 skeleton rounded-3xl" /></div>;

  if (!isHost) {
    return (
      <div className="min-h-[50vh] flex flex-col items-center justify-center text-center gap-4 px-6">
        <p className="font-heading font-bold text-xl text-dark">{t("pasHote")}</p>
        <Link href="/hote" className="bg-primary text-white font-bold px-6 py-3 rounded-xl">{t("devenirHote")}</Link>
      </div>
    );
  }

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ["hebergements"] });
    queryClient.invalidateQueries({ queryKey: ["villes"] });
  };

  const toggleAvailability = async (h: Hebergement) => {
    try {
      await api.patch(`/v1/hebergements/${h.id}/`, { is_available: !h.is_available });
      toast.success(h.is_available ? t("masquee") : t("visible"));
      refresh();
    } catch (err) {
      toast.error(apiErrorMessage(err));
    }
  };

  const remove = async (h: Hebergement) => {
    if (!window.confirm(t("supprimerQuestion", { nom: h.name }))) return;
    try {
      await api.delete(`/v1/hebergements/${h.id}/`);
      toast.success(t("supprimee"));
      refresh();
    } catch (err) {
      toast.error(apiErrorMessage(err));
    }
  };

  const upcoming = reservations.filter((r) => r.status === "confirmed" && r.check_out >= isoDate());
  // Host's share (price of the nights minus the commission) on confirmed stays
  const revenue = reservations.filter((r) => r.status === "confirmed").reduce((s, r) => s + r.montants.montant_hote, 0);

  if (editing) {
    const formulaire = (
      <HebergementForm
        initial={editing === "new" ? undefined : editing}
        onCancel={() => setEditing(null)}
        onSaved={(h) => {
          toast.success(editing === "new" ? t("publiee") : t("miseAJour"));
          setEditing(null);
          refresh();
          if (editing === "new") router.push(`/hebergements/${h.id}`);
        }}
      />
    );
    return (
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8">
        <h1 className="font-heading font-bold text-2xl sm:text-3xl text-dark mb-6">{editing === "new" ? t("nouvelle") : t("modifier")}</h1>
        <div className="bg-white rounded-3xl shadow-card p-5 sm:p-8">
          {/* Pre-launch: a new listing starts with the pre-registration (shown only if still to be accepted) */}
          {editing === "new" ? <PreinscriptionHote onCancel={() => setEditing(null)}>{formulaire}</PreinscriptionHote> : formulaire}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8 md:py-12">
      <FenetreOuverture ouverte={fenetre} onCreer={creerDepuisFenetre} onFermer={fermerFenetre} />
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-8">
        <div>
          <h1 className="font-heading font-bold text-2xl sm:text-3xl text-dark">{t("titre")}</h1>
          <p className="text-gray-500 text-sm mt-1">{t("sousTitre")}</p>
        </div>
        <button onClick={nouvelle} className="flex items-center justify-center gap-2 bg-primary text-white font-bold px-5 py-3 rounded-xl shadow-button hover:bg-primary-600">
          <Plus size={18} /> {t("nouvelle")}
        </button>
      </div>

      <CandidatureHote nbAnnonces={annonces.length} onNouvelle={nouvelle} />

      <div className="grid grid-cols-3 gap-3 sm:gap-4 mb-8">
        {[
          { label: t("stats.annonces"), value: annonces.length },
          { label: t("stats.aVenir"), value: upcoming.length },
          { label: t("stats.revenus"), value: formatPrice(revenue) },
        ].map((s) => (
          <div key={s.label} className="bg-white rounded-2xl p-4 sm:p-5 border border-gray-100 shadow-sm min-w-0">
            <p className="text-xs text-muted font-medium">{s.label}</p>
            <p className="font-heading font-bold text-dark text-lg sm:text-2xl mt-1 truncate">{s.value}</p>
          </div>
        ))}
      </div>

      <div className="flex gap-6 border-b border-gray-200 mb-6 overflow-x-auto scrollbar-hide" role="tablist">
        {([["annonces", t("onglets.annonces", { nombre: annonces.length })], ["reservations", t("onglets.reservations", { nombre: reservations.length })], ["revenus", t("onglets.revenus")]] as const).map(([id, label]) => (
          <button key={id} role="tab" aria-selected={tab === id} onClick={() => setTab(id)}
            className={cn("pb-3 text-sm font-bold whitespace-nowrap border-b-2 transition-colors", tab === id ? "text-primary border-primary" : "text-gray-400 border-transparent hover:text-dark")}>
            {label}
          </button>
        ))}
      </div>

      {tab === "revenus" ? (
        <RevenusHote />
      ) : tab === "annonces" ? (
        isLoading ? (
          <div className="space-y-4">{[0, 1].map((i) => <div key={i} className="h-36 skeleton rounded-2xl" />)}</div>
        ) : annonces.length === 0 ? (
          <div className="bg-white rounded-3xl p-10 sm:p-16 text-center border border-gray-100">
            <p className="text-gray-500 mb-4">{t("aucuneAnnonce")}</p>
            <button onClick={nouvelle} className="bg-primary text-white font-bold px-6 py-3 rounded-xl">{t("publierPremier")}</button>
          </div>
        ) : (
          <div className="space-y-4">
            {annonces.map((h) => (
              <article key={h.id} className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden flex flex-col sm:flex-row">
                <Link href={`/hebergements/${h.id}`} className="sm:w-48 h-40 sm:h-auto flex-shrink-0 relative">
                  <img src={h.image_url || FALLBACK_IMAGE} alt={h.name} className={cn("w-full h-full object-cover", (!h.is_available || h.statut_verification !== "verifiee") && "grayscale opacity-60")} />
                  {!h.is_available && <span className="absolute top-3 left-3 bg-dark text-white text-[10px] font-bold uppercase px-2 py-1 rounded-full">{t("masqueeBadge")}</span>}
                </Link>
                <div className="flex-1 p-5 min-w-0 flex flex-col">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <h2 className="font-heading font-bold text-dark truncate">{h.name}</h2>
                      <p className="flex items-center gap-1 text-sm text-gray-500 mt-1"><MapPin size={13} className="text-primary" />{h.city} · {TYPE_LABELS[h.type]} · {t("pers", { nombre: h.max_guests })}</p>
                    </div>
                    <p className="font-heading font-bold text-primary whitespace-nowrap">{formatPrice(h.price_per_night)}<span className="text-xs text-gray-400 font-normal">/nuit</span></p>
                  </div>
                  <RatingBadge rating={h.rating} count={h.review_count} variant="full" className="mt-2" />
                  {h.surface_m2 == null && (
                    <button type="button" onClick={() => setEditing(h)} className="relative zone-tactile flex items-start gap-1.5 text-left text-xs font-semibold text-amber-800 mt-2 hover:underline">
                      <AlertTriangle size={14} className="flex-shrink-0 mt-px" /> {tAnnonce("detailsManquants")}
                    </button>
                  )}
                  {h.statut_verification === "verifiee" && prelancement ? (
                    <div className="mt-3 text-sm bg-primary/5 text-primary rounded-xl px-3 py-2">
                      <p className="flex flex-wrap items-center gap-x-3 gap-y-1">
                        <span className="flex items-center gap-1.5 text-xs font-bold text-green-700"><ShieldCheck size={14} aria-hidden /> {tVerif("verifiee")}</span>
                        <span className="inline-flex items-center gap-1 bg-accent/15 text-amber-900 text-[11px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-full">
                          <Hourglass size={12} aria-hidden /> {tPre("badge")}
                        </span>
                      </p>
                      <p className="mt-1 text-xs text-gray-600">{tPre("badgeAide")}</p>
                    </div>
                  ) : h.statut_verification === "verifiee" && h.en_ligne === false && h.is_available ? (
                    <div className="mt-3 text-sm bg-amber-50 text-amber-900 rounded-xl px-3 py-2">
                      <p className="flex items-center gap-1.5 font-bold"><AlertTriangle size={14} aria-hidden /> {tPre("contratRequis")}</p>
                      <Link href="/hote/espace/contrat" className="inline-block mt-1 text-xs font-bold underline">{tPre("signerContrat")}</Link>
                    </div>
                  ) : h.statut_verification === "verifiee" ? (
                    <p className="flex items-center gap-1.5 text-xs font-bold text-green-700 mt-2"><ShieldCheck size={14} /> {tVerif("verifiee")}</p>
                  ) : h.statut_verification === "refusee" ? (
                    <div role="alert" className="mt-3 text-sm bg-red-50 text-red-800 rounded-xl px-3 py-2">
                      <p className="flex items-center gap-1.5 font-bold"><AlertTriangle size={14} /> {tVerif("refusee")}</p>
                      {h.motif_refus && <p className="mt-1">« {h.motif_refus} »</p>}
                      <p className="mt-1 text-xs">{tVerif("refuseeAide")}</p>
                    </div>
                  ) : (
                    <div className="mt-3 text-sm bg-amber-50 text-amber-900 rounded-xl px-3 py-2">
                      <p className="flex items-center gap-1.5 font-bold"><Clock size={14} /> {tVerif("enAttente")}</p>
                      <p className="mt-1 text-xs">{tVerif("enAttenteAide")}</p>
                    </div>
                  )}
                  <div className="flex flex-wrap gap-2 mt-auto pt-4">
                    <button onClick={() => setEditing(h)} className="flex items-center gap-1.5 px-4 py-2 rounded-full bg-gray-100 text-dark text-sm font-medium hover:bg-gray-200"><Pencil size={14} /> {t("modifierCourt")}</button>
                    <Link href={`/hote/espace/calendrier/${h.id}`} className="flex items-center gap-1.5 px-4 py-2 rounded-full bg-gray-100 text-dark text-sm font-medium hover:bg-gray-200"><CalendarDays size={14} /> {t("calendrier")}</Link>
                    <Link href={`/hote/espace/types/${h.id}`} className="flex items-center gap-1.5 px-4 py-2 rounded-full bg-gray-100 text-dark text-sm font-medium hover:bg-gray-200"><BedDouble size={14} /> {t("typesLogement")}</Link>
                    <button onClick={() => toggleAvailability(h)} className="flex items-center gap-1.5 px-4 py-2 rounded-full bg-gray-100 text-dark text-sm font-medium hover:bg-gray-200">
                      {h.is_available ? <><EyeOff size={14} /> {t("masquer")}</> : <><Eye size={14} /> {t("publier")}</>}
                    </button>
                    <button onClick={() => remove(h)} className="flex items-center gap-1.5 px-4 py-2 rounded-full bg-red-50 text-red-700 text-sm font-medium hover:bg-red-100"><Trash2 size={14} /> Supprimer</button>
                  </div>
                </div>
              </article>
            ))}
          </div>
        )
      ) : resLoading ? (
        <div className="h-36 skeleton rounded-2xl" />
      ) : reservations.length === 0 ? (
        <div className="bg-white rounded-3xl p-10 sm:p-16 text-center border border-gray-100 text-gray-500">{t("aucuneResa")}</div>
      ) : (
        <div className="space-y-3">
          {reservations.map((r) => (
            <article key={r.id} className="bg-white rounded-2xl border border-gray-100 p-5 flex flex-col md:flex-row md:items-center gap-3 md:gap-6">
              <div className="flex-1 min-w-0">
                <p className="font-heading font-bold text-dark truncate">{r.hebergement_detail.name}</p>
                <p className="text-sm text-gray-500">{t("par", { nom: r.guest_name })} · <span className="font-mono text-xs">{r.reference}</span></p>
                {r.message && <p className="text-sm text-gray-600 mt-2 bg-gray-50 rounded-xl px-3 py-2 italic">« {r.message} »</p>}
              </div>
              <div className="flex flex-wrap items-center gap-x-5 gap-y-1 text-sm text-gray-600">
                <span className="flex items-center gap-1.5"><Calendar size={14} className="text-primary" />{formatDate(r.check_in)} → {formatDate(r.check_out)}</span>
                <span className="flex items-center gap-1.5"><Users size={14} className="text-primary" />{r.guests_count}</span>
              </div>
              <div className="flex items-center justify-between md:flex-col md:items-end gap-1">
                <span className="font-heading font-bold text-dark" title={t("montantHoteAide")}>
                  {formatPrice(r.montants.montant_hote)} <span className="text-xs font-normal text-gray-600">{t("pourVous")}</span>
                </span>
                <span className={cn("text-xs font-bold px-2.5 py-1 rounded-full",
                  r.status === "cancelled" ? "bg-red-100 text-red-700" : r.status === "pending" ? "bg-amber-100 text-amber-800" : "bg-green-100 text-green-700")}>
                  {r.status === "cancelled"
                    ? t("annulee")
                    : r.status === "pending"
                      ? t("enAttentePaiement")
                      : `${r.paiement === "reussi" ? t("payee") : t("confirmee")} · ${tRes(`moyens.${PAYMENT_LABELS[r.payment_method] ?? "mobileMoney"}`)}`}
                </span>
                {r.status === "confirmed" && (
                  <button
                    onClick={() => contacterVoyageur(r)} disabled={contactId === r.id}
                    className="mt-1 flex items-center gap-1.5 px-4 py-2 rounded-full border border-primary/30 text-primary text-sm font-semibold hover:bg-primary/5 disabled:opacity-50"
                  >
                    <MessageCircle size={14} /> {contactId === r.id ? t("ouverture") : t("contacterNom", { nom: r.guest_name.split(" ")[0] })}
                  </button>
                )}
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}

export default function EspaceHotePage() {
  return (
    <Suspense>
      <EspaceHoteContent />
    </Suspense>
  );
}
