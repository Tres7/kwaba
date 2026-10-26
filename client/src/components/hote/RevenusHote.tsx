"use client";

import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle, Clock, Loader2, Smartphone, Wallet } from "lucide-react";
import { toast } from "sonner";
import api, { apiErrorMessage } from "@/lib/api";
import { useConfigPaiement } from "@/lib/paiement";
import { cn, formatDate, formatPrice } from "@/lib/utils";
import Select from "@/components/ui/Select";
import FormField from "@/components/ui/FormField";
import type { ProfilVersement, Revenus, StatutVersement } from "@/types/api/paiement";
import { useTranslations } from "next-intl";
import { PAYS } from "@/lib/give";

const STATUTS: Record<StatutVersement, { label: string; className: string }> = {
  planifie: { label: "prevu", className: "bg-gray-100 text-dark" },
  en_cours: { label: "enCours", className: "bg-amber-100 text-amber-800" },
  envoye: { label: "verse", className: "bg-green-100 text-green-800" },
  echoue: { label: "aVerifier", className: "bg-red-100 text-red-700" },
};

export default function RevenusHote() {
  const t = useTranslations("revenus");
  const { data: config } = useConfigPaiement();
  const { data: revenus, isLoading } = useQuery({
    queryKey: ["paiements", "revenus"],
    queryFn: async () => (await api.get<Revenus>("/v1/paiements/revenus/")).data,
  });
  // This host's rate (8 %, 12 % for a hotel, 5 % during the Founders Programme)
  const commission = revenus?.commission_pourcent ?? (config ? Math.round(config.commission_hote * 100) : 8);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4">
        {[
          { label: t("totaux.aVenir"), value: revenus?.totaux.a_venir, icon: Clock, hint: t("totaux.aVenirAide") },
          { label: t("totaux.enCours"), value: revenus?.totaux.en_cours, icon: Loader2, hint: t("totaux.enCoursAide") },
          { label: t("totaux.verse"), value: revenus?.totaux.verse, icon: CheckCircle, hint: t("totaux.commission", { montant: formatPrice(revenus?.totaux.commission ?? 0) }) },
        ].map(({ label, value, icon: Icon, hint }) => (
          <div key={label} className="bg-white rounded-2xl p-5 border border-gray-100 shadow-sm">
            <p className="flex items-center gap-2 text-xs text-muted font-medium"><Icon size={14} className="text-primary" /> {label}</p>
            <p className="font-heading font-bold text-dark text-2xl mt-1">{isLoading ? "…" : formatPrice(value ?? 0)}</p>
            <p className="text-xs text-gray-600 mt-1">{hint}</p>
          </div>
        ))}
      </div>

      <ProfilVersementForm manquant={revenus ? !revenus.profil_complet : false} />

      <section className="bg-white rounded-3xl border border-gray-100 p-5 sm:p-6">
        <h2 className="font-heading font-bold text-dark text-lg">{t("versements")}</h2>
        <p className="text-sm text-gray-600 mt-1">
          {t("explication", { commission })}
        </p>
        {isLoading ? (
          <div className="h-24 skeleton rounded-2xl mt-4" />
        ) : !revenus?.versements.length ? (
          <p className="text-sm text-gray-600 mt-4 bg-gray-50 rounded-2xl p-6 text-center">{t("aucun")}</p>
        ) : (
          <ul className="mt-4 divide-y divide-gray-100">
            {revenus.versements.map((v) => (
              <li key={v.id} className="py-4 flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-6">
                <div className="flex-1 min-w-0">
                  <p className="font-bold text-dark text-sm truncate">{v.hebergement}</p>
                  <p className="text-xs text-gray-600">
                    {v.voyageur} · {formatDate(v.check_in)} → {formatDate(v.check_out)} · <span className="font-mono">{v.reference}</span>
                  </p>
                  {v.probleme && (
                    <p className="flex items-start gap-1.5 text-xs text-red-700 mt-1"><AlertTriangle size={12} className="flex-shrink-0 mt-0.5" /> {v.probleme}</p>
                  )}
                </div>
                <div className="text-xs text-gray-600 sm:text-right">
                  <p>{t("deCommission", { brut: formatPrice(v.montant_brut), commission: formatPrice(v.commission) })}</p>
                  <p>{v.statut === "envoye" && v.envoye_le ? t("verseLe", { date: formatDate(v.envoye_le.slice(0, 10)) }) : t("prevuLe", { date: formatDate(v.date_prevue.slice(0, 10)) })}</p>
                </div>
                <div className="flex sm:flex-col items-center sm:items-end justify-between gap-1">
                  <span className="font-heading font-bold text-dark">{formatPrice(v.montant)}</span>
                  <span className={cn("text-xs font-bold px-2.5 py-1 rounded-full", STATUTS[v.statut].className)}>{t(`statuts.${STATUTS[v.statut].label}`)}</span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function ProfilVersementForm({ manquant }: { manquant: boolean }) {
  const t = useTranslations("revenus");
  const tD = useTranslations("remboursementDialog");
  const queryClient = useQueryClient();
  const { data: config } = useConfigPaiement();
  const { data: profil, isLoading } = useQuery({
    queryKey: ["paiements", "profil-versement"],
    queryFn: async () => (await api.get<ProfilVersement | null>("/v1/paiements/profil-versement/")).data,
  });

  const [form, setForm] = useState<ProfilVersement>({ pays: "TG", operateur: "", numero: "", titulaire: "" });
  const [erreurs, setErreurs] = useState<Record<string, string>>({});
  const [envoi, setEnvoi] = useState(false);
  const [edition, setEdition] = useState(false);

  useEffect(() => {
    if (profil) setForm(profil);
  }, [profil]);

  const pays = config?.pays.find((p) => p.code === form.pays);
  const operateurs = pays?.operateurs ?? [];
  const operateur = operateurs.some((o) => o.code === form.operateur) ? form.operateur : operateurs[0]?.code ?? "";

  const enregistrer = async (e: React.FormEvent) => {
    e.preventDefault();
    setEnvoi(true);
    setErreurs({});
    try {
      const res = await api.put<ProfilVersement>("/v1/paiements/profil-versement/", { ...form, operateur });
      queryClient.setQueryData(["paiements", "profil-versement"], res.data);
      queryClient.invalidateQueries({ queryKey: ["paiements", "revenus"] });
      toast.success(t("enregistrees"));
      setEdition(false);
    } catch (err) {
      const data = (err as { response?: { data?: Record<string, string[] | string> } }).response?.data;
      if (data && typeof data === "object" && !("detail" in data)) {
        setErreurs(Object.fromEntries(Object.entries(data).map(([k, v]) => [k, Array.isArray(v) ? v[0] : String(v)])));
      } else {
        toast.error(apiErrorMessage(err));
      }
    } finally {
      setEnvoi(false);
    }
  };

  if (isLoading || !config) return <div className="h-40 skeleton rounded-3xl" />;

  const nomOperateur = (code: string) => config.pays.flatMap((p) => p.operateurs).find((o) => o.code === code)?.nom ?? code;

  if (profil && !edition) {
    const indicatif = config.pays.find((p) => p.code === profil.pays)?.indicatif;
    return (
      <section className="bg-white rounded-3xl border border-gray-100 p-5 sm:p-6 flex flex-col sm:flex-row sm:items-center gap-4">
        <div className="w-12 h-12 rounded-2xl bg-secondary/10 text-secondary flex items-center justify-center flex-shrink-0"><Smartphone size={22} /></div>
        <div className="flex-1 min-w-0">
          <h2 className="font-heading font-bold text-dark">{t("arriventSur")}</h2>
          <p className="text-sm text-gray-600">{nomOperateur(profil.operateur)} · +{indicatif} {profil.numero} · {profil.titulaire}</p>
        </div>
        <button onClick={() => setEdition(true)} className="px-5 py-2.5 rounded-full border border-gray-200 text-sm font-bold text-dark hover:bg-gray-50">{t("modifier")}</button>
      </section>
    );
  }

  return (
    <section className={cn("bg-white rounded-3xl border p-5 sm:p-6", manquant ? "border-amber-300" : "border-gray-100")}>
      <h2 className="flex items-center gap-2 font-heading font-bold text-dark text-lg"><Wallet size={20} className="text-primary" /> {t("ouRecevoir")}</h2>
      <p className="text-sm text-gray-600 mt-1">
        {manquant
          ? t("manquant")
          : t("envoyeSur")}
      </p>
      <form method="post" onSubmit={enregistrer} className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-5" noValidate>
        <div>
          <p className="block text-xs font-bold text-dark uppercase tracking-wide mb-2" id="pays-label">{tD("pays")}</p>
          <Select
            label={tD("pays")} value={form.pays}
            onChange={(v) => setForm({ ...form, pays: v as ProfilVersement["pays"], operateur: "" })}
            options={config.pays.map((p) => ({ value: p.code, label: PAYS[p.code] ?? p.nom }))}
          />
        </div>
        <div>
          <p className="block text-xs font-bold text-dark uppercase tracking-wide mb-2">{tD("operateur")}</p>
          <Select
            label={tD("operateurMM")} value={operateur}
            onChange={(v) => setForm({ ...form, operateur: v })}
            options={operateurs.map((o) => ({ value: o.code, label: o.nom }))}
          />
          {erreurs.operateur && <p className="text-xs text-red-600 mt-1.5 ml-1">{erreurs.operateur}</p>}
        </div>
        <FormField
          label={tD("numero", { indicatif: pays?.indicatif ?? "" })} id="v-numero" inputMode="numeric" autoComplete="tel-national"
          value={form.numero} onChange={(e) => setForm({ ...form, numero: e.target.value })}
          placeholder={pays ? "0".repeat(pays.chiffres) : ""} error={erreurs.numero}
          hint={pays ? tD("chiffres", { nombre: pays.chiffres }) : undefined} required
        />
        <FormField
          label={t("titulaire")} id="v-titulaire" autoComplete="name"
          value={form.titulaire} onChange={(e) => setForm({ ...form, titulaire: e.target.value })}
          error={erreurs.titulaire} hint={t("titulaireAide")} required
        />
        <div className="sm:col-span-2 flex flex-wrap gap-3 justify-end">
          {profil && (
            <button type="button" onClick={() => { setForm(profil); setEdition(false); setErreurs({}); }} className="px-5 py-3 rounded-xl border border-gray-200 text-sm font-bold text-dark">
              {t("annuler")}
            </button>
          )}
          <button type="submit" disabled={envoi} className="px-6 py-3 rounded-xl bg-primary text-white text-sm font-bold hover:bg-primary-600 disabled:opacity-60">
            {envoi ? t("enregistrement") : t("enregistrer")}
          </button>
        </div>
      </form>
    </section>
  );
}
