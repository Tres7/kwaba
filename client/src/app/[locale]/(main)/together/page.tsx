"use client";

import { Link, useRouter } from "@/i18n/navigation";
import { useState } from "react";
import { useSession } from "next-auth/react";
import { useQuery } from "@tanstack/react-query";
import { CalendarDays, Link2, MapPin, Plus, Users, Vote, Wallet } from "lucide-react";
import api, { apiErrorMessage } from "@/lib/api";
import { isoDate } from "@/lib/utils";
import FormField from "@/components/ui/FormField";
import Stepper from "@/components/ui/Stepper";
import type { Voyage, VoyageResume } from "@/types/api/voyage";
import { useTranslations } from "next-intl";
import PageHero from "@/components/layout/PageHero";
import { useFormat } from "@/lib/format";

const ATOUTS = [
  { icon: Link2, id: "lien" },
  { icon: Vote, id: "vote" },
  { icon: Wallet, id: "budget" },
  { icon: CalendarDays, id: "itineraire" },
];

export default function TogetherPage() {
  const { formatDate } = useFormat();
  const t = useTranslations("together");
  const router = useRouter();
  const { status } = useSession();
  const connecte = status === "authenticated";
  const [creation, setCreation] = useState(false);
  const [form, setForm] = useState({ nom: "", destination: "", date_debut: "", date_fin: "", nb_voyageurs: 4 });
  const [erreurs, setErreurs] = useState<Record<string, string>>({});
  const [envoi, setEnvoi] = useState(false);

  const { data: voyages = [], isLoading } = useQuery({
    queryKey: ["voyages"],
    queryFn: async () => (await api.get<{ results: VoyageResume[] }>("/v1/voyages/")).data.results,
    enabled: connecte,
  });

  const creer = async (e: React.FormEvent) => {
    e.preventDefault();
    setEnvoi(true);
    setErreurs({});
    try {
      const res = await api.post<Voyage>("/v1/voyages/", {
        ...form, date_debut: form.date_debut || null, date_fin: form.date_fin || null,
      });
      router.push(`/together/${res.data.id}?nouveau=1`);
    } catch (err) {
      const data = (err as { response?: { data?: Record<string, string[] | string> } }).response?.data;
      if (data && typeof data === "object" && !("detail" in data)) {
        setErreurs(Object.fromEntries(Object.entries(data).map(([k, v]) => [k, Array.isArray(v) ? v[0] : String(v)])));
      } else {
        setErreurs({ general: apiErrorMessage(err, t("erreurCreation")) });
      }
      setEnvoi(false);
    }
  };

  return (
    <div className="bg-light pb-12">
      <PageHero surtitre={<><Users size={16} /> Kwa-Ba Together</>} titre={t("titre")} sousTitre={t("sousTitre")}>
          {connecte ? (
            <button onClick={() => setCreation(true)} className="mt-6 inline-flex items-center gap-2 bg-white text-primary-700 font-bold px-6 py-3 rounded-xl hover:bg-orange-50">
              <Plus size={18} /> {t("creer")}
            </button>
          ) : (
            <Link href="/login?callbackUrl=/together" className="mt-6 inline-flex items-center gap-2 bg-white text-primary-700 font-bold px-6 py-3 rounded-xl">
              {t("seConnecter")}
            </Link>
          )}
      </PageHero>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8 space-y-8">
        {creation && (
          <form method="post" onSubmit={creer} noValidate className="bg-white rounded-3xl border border-gray-100 shadow-card p-5 sm:p-8 space-y-4">
            <h2 className="font-heading font-bold text-dark text-xl">{t("nouveau")}</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <FormField label={t("nomVoyage")} id="v-nom" value={form.nom} onChange={(e) => setForm({ ...form, nom: e.target.value })}
                placeholder={t("nomExemple")} error={erreurs.nom} maxLength={80} required />
              <FormField label={t("destination")} id="v-destination" value={form.destination} onChange={(e) => setForm({ ...form, destination: e.target.value })}
                placeholder="Abidjan" error={erreurs.destination} required />
              <FormField label={t("arrivee")} id="v-debut" type="date" min={isoDate()} value={form.date_debut}
                onChange={(e) => setForm({ ...form, date_debut: e.target.value })} hint={t("facultatif")} />
              <FormField label={t("depart")} id="v-fin" type="date" min={form.date_debut || isoDate()} value={form.date_fin}
                onChange={(e) => setForm({ ...form, date_fin: e.target.value })} error={erreurs.date_fin} />
            </div>
            <Stepper label={t("nbVoyageurs")} hint={t("nbVoyageursAide")} value={form.nb_voyageurs}
              onChange={(n) => setForm({ ...form, nb_voyageurs: n })} min={1} max={20} className="max-w-sm" />
            {erreurs.general && <p role="alert" className="text-sm text-red-700 bg-red-50 rounded-xl p-3">{erreurs.general}</p>}
            <div className="flex gap-3 justify-end">
              <button type="button" onClick={() => setCreation(false)} className="px-5 py-3 rounded-xl border border-gray-200 text-sm font-bold text-dark">{t("annuler")}</button>
              <button type="submit" disabled={envoi || !form.nom.trim() || !form.destination.trim()}
                className="px-6 py-3 rounded-xl bg-primary text-white text-sm font-bold disabled:opacity-60">
                {envoi ? t("creation") : t("creerInviter")}
              </button>
            </div>
          </form>
        )}

        {connecte && (
          <section>
            <h2 className="font-heading font-bold text-dark text-xl mb-4">{t("mesVoyages")}</h2>
            {isLoading ? (
              <div className="grid sm:grid-cols-2 gap-4">{[0, 1].map((i) => <div key={i} className="h-32 skeleton rounded-2xl" />)}</div>
            ) : voyages.length === 0 ? (
              <p className="bg-white rounded-2xl border border-gray-100 p-8 text-center text-gray-600">
                {t("aucun")}
              </p>
            ) : (
              <ul className="grid sm:grid-cols-2 gap-4">
                {voyages.map((v) => (
                  <li key={v.id}>
                    <Link href={`/together/${v.id}`} className="block bg-white rounded-2xl border border-gray-100 p-5 hover:shadow-card transition-shadow">
                      <p className="font-heading font-bold text-dark text-lg">{v.nom}</p>
                      <p className="flex items-center gap-1.5 text-sm text-gray-600 mt-1"><MapPin size={14} className="text-primary" /> {v.destination}
                        {v.date_debut && v.date_fin && <> · {formatDate(v.date_debut)} → {formatDate(v.date_fin)}</>}
                      </p>
                      <p className="text-sm text-gray-600 mt-3">
                        {t("membres", { nombre: v.nb_membres })} · {t("propositions", { nombre: v.nb_propositions })}
                        {" · "}{v.est_organisateur ? t("vousOrganisez") : t("organisePar", { nom: v.organisateur })}
                      </p>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </section>
        )}

        <section className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {ATOUTS.map(({ icon: Icon, id }) => (
            <div key={id} className="bg-white rounded-2xl border border-gray-100 p-5">
              <div className="w-11 h-11 rounded-xl bg-primary/10 text-primary flex items-center justify-center"><Icon size={20} /></div>
              <h3 className="font-heading font-bold text-dark mt-3">{t(`atouts.${id}.titre`)}</h3>
              <p className="text-sm text-gray-600 mt-1">{t(`atouts.${id}.texte`)}</p>
            </div>
          ))}
        </section>
      </div>
    </div>
  );
}
