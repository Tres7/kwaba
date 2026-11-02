"use client";

import FormField from "@/components/ui/FormField";
import { useState } from "react";
import { MapPin, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { useLocale, useTranslations } from "next-intl";
import { useFormat } from "@/lib/format";
import { ajouterEtape, retirerEtape } from "./api";
import { messageErreur } from "./erreurs";
import type { SectionVoyage, Voyage } from "./types";

export default function Itineraire({ v, appliquer, recharger }: SectionVoyage) {
  const { formatDate } = useFormat();
  const locale = useLocale();
  const t = useTranslations("voyage");
  const [form, setForm] = useState({ date: v.date_debut ?? "", heure: "", titre: "", lieu: "", details: "" });
  const [envoi, setEnvoi] = useState(false);

  const ajouter = async (e: React.FormEvent) => {
    e.preventDefault();
    setEnvoi(true);
    try {
      appliquer(await ajouterEtape(v.id, { ...form, heure: form.heure || null }));
      setForm({ ...form, heure: "", titre: "", lieu: "", details: "" });
    } catch (err) {
      toast.error(messageErreur(err, t("etapeErreur")));
    } finally {
      setEnvoi(false);
    }
  };

  const jours = v.etapes.reduce<Record<string, Voyage["etapes"]>>((acc, e) => ({ ...acc, [e.date]: [...(acc[e.date] ?? []), e] }), {});

  return (
    <div className="grid lg:grid-cols-5 gap-6">
      <div className="lg:col-span-3 space-y-4">
        {Object.keys(jours).length === 0 ? (
          <p className="bg-white rounded-2xl border border-gray-100 p-8 text-center text-gray-600">{t("itineraireVide")}</p>
        ) : Object.entries(jours).map(([jour, etapes]) => (
          <section key={jour} className="bg-white rounded-2xl border border-gray-100 p-5">
            <h3 className="font-heading font-bold text-dark capitalize">{formatDate(`${jour}T12:00:00`, { weekday: "long", day: "numeric", month: "long" })}</h3>
            <ol className="mt-3 space-y-3 border-l-2 border-primary/20 pl-4">
              {etapes.map((e) => (
                <li key={e.id} className="relative">
                  <span className="absolute -left-[23px] top-1 w-3 h-3 rounded-full bg-primary" aria-hidden="true" />
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="text-sm font-bold text-dark">{e.heure && <span className="text-primary mr-2">{locale === "en" ? e.heure.slice(0, 5) : e.heure.replace(":", " h ")}</span>}{e.titre}</p>
                      {e.lieu && <p className="text-xs text-gray-600 flex items-center gap-1"><MapPin size={11} /> {e.lieu}</p>}
                      {e.details && <p className="text-sm text-gray-700 mt-1">{e.details}</p>}
                      <p className="text-[11px] text-gray-500 mt-0.5">{t("ajoutePar", { nom: e.ajoute_par })}</p>
                    </div>
                    {e.peut_supprimer && (
                      <button onClick={async () => { await retirerEtape(v.id, e.id); recharger(); }}
                        aria-label={t("supprimer", { titre: e.titre })} className="p-1.5 rounded-full text-gray-500 hover:text-red-700 hover:bg-red-50"><Trash2 size={14} /></button>
                    )}
                  </div>
                </li>
              ))}
            </ol>
          </section>
        ))}
      </div>
      <form method="post" onSubmit={ajouter} className="lg:col-span-2 bg-white rounded-2xl border border-gray-100 p-5 space-y-3 h-fit">
        <h3 className="font-heading font-bold text-dark">{t("ajouterEtape")}</h3>
        <div className="grid grid-cols-2 gap-3">
          <FormField label={t("jour")} id="e-date" type="date" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })}
            min={v.date_debut ?? undefined} max={v.date_fin ?? undefined} required />
          <FormField label={t("heure")} id="e-heure" type="time" value={form.heure} onChange={(e) => setForm({ ...form, heure: e.target.value })} />
        </div>
        <FormField label={t("activite")} id="e-titre" value={form.titre} onChange={(e) => setForm({ ...form, titre: e.target.value })} placeholder={t("activiteExemple")} maxLength={120} required />
        <FormField label={t("lieu")} id="e-lieu" value={form.lieu} onChange={(e) => setForm({ ...form, lieu: e.target.value })} placeholder={t("facultatif")} />
        <FormField label={t("details")} id="e-details" value={form.details} onChange={(e) => setForm({ ...form, details: e.target.value })} placeholder={t("detailsExemple")} maxLength={500} />
        <button type="submit" disabled={envoi || !form.date || !form.titre.trim()} className="w-full py-3 rounded-xl bg-primary text-white text-sm font-bold disabled:opacity-60">
          {envoi ? t("ajout") : t("ajouterItineraire")}
        </button>
      </form>
    </div>
  );
}
