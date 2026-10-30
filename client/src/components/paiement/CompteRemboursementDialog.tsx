"use client";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Smartphone, X } from "lucide-react";
import api, { apiErrorMessage } from "@/lib/api";
import { useConfigPaiement } from "@/lib/paiement";
import Select from "@/components/ui/Select";
import FormField from "@/components/ui/FormField";
import type { PaysPaiement } from "@/types/api/paiement";
import { useTranslations } from "next-intl";
import { useTextesGive } from "@/lib/give";
import { useFormat } from "@/lib/format";

interface Props {
  /** Route that saves the account (booking or transfer). */
  endpoint: string;
  montant: number;
  onClose: () => void;
  onDone: () => void;
}

/** Asks the traveller for the Mobile Money account to refund them on (FedaPay does not give the charged number). */
export default function CompteRemboursementDialog({ endpoint, montant, onClose, onDone }: Props) {
  const { formatPrice } = useFormat();
  const { PAYS } = useTextesGive();
  const t = useTranslations("remboursementDialog");
  const { data: config } = useConfigPaiement();
  const [pays, setPays] = useState<PaysPaiement["code"]>("TG");
  const [operateurChoisi, setOperateur] = useState("");
  const [numero, setNumero] = useState("");
  const [erreurs, setErreurs] = useState<Record<string, string>>({});
  const [envoi, setEnvoi] = useState(false);
  const panneau = useRef<HTMLDivElement>(null);

  const infos = config?.pays.find((p) => p.code === pays);
  const operateurs = infos?.operateurs ?? [];
  const operateur = operateurs.some((o) => o.code === operateurChoisi) ? operateurChoisi : operateurs[0]?.code ?? "";

  useEffect(() => {
    const precedent = document.activeElement as HTMLElement | null;
    panneau.current?.querySelector<HTMLElement>("button, input")?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
      precedent?.focus();
    };
  }, [onClose]);

  const envoyer = async (e: React.FormEvent) => {
    e.preventDefault();
    setEnvoi(true);
    setErreurs({});
    try {
      await api.put(endpoint, { pays, operateur, numero });
      onDone();
    } catch (err) {
      const data = (err as { response?: { data?: Record<string, string[] | string> } }).response?.data;
      if (data && typeof data === "object" && !("detail" in data)) {
        setErreurs(Object.fromEntries(Object.entries(data).map(([k, v]) => [k, Array.isArray(v) ? v[0] : String(v)])));
      } else {
        setErreurs({ general: apiErrorMessage(err, t("erreurNumero")) });
      }
      setEnvoi(false);
    }
  };

  return createPortal(
    <div className="fixed inset-0 z-[70] flex items-end sm:items-center justify-center p-0 sm:p-4">
      <div className="absolute inset-0 bg-dark/50" onClick={onClose} aria-hidden="true" />
      <div
        ref={panneau} role="dialog" aria-modal="true" aria-labelledby="remb-titre"
        className="relative w-full sm:max-w-md bg-white rounded-t-3xl sm:rounded-3xl shadow-xl p-6 max-h-[90vh] overflow-y-auto"
      >
        <button onClick={onClose} aria-label={t("fermer")} className="absolute top-4 right-4 w-9 h-9 rounded-full flex items-center justify-center text-gray-600 hover:bg-gray-100">
          <X size={18} />
        </button>
        <div className="w-12 h-12 rounded-2xl bg-secondary/10 text-secondary flex items-center justify-center mb-4"><Smartphone size={22} /></div>
        <h2 id="remb-titre" className="font-heading font-bold text-dark text-xl pr-8">{t("titre")}</h2>
        <p className="text-sm text-gray-600 mt-2">
          {t.rich("texte", { montant: formatPrice(montant), strong: (x) => <strong>{x}</strong> })}
        </p>

        {!config ? (
          <div className="h-48 skeleton rounded-2xl mt-5" />
        ) : (
          <form method="post" onSubmit={envoyer} className="space-y-4 mt-5" noValidate>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <p className="block text-xs font-bold text-dark uppercase tracking-wide mb-2">{t("pays")}</p>
                <Select label={t("pays")} value={pays} onChange={(v) => setPays(v as PaysPaiement["code"])}
                  options={config.pays.map((p) => ({ value: p.code, label: PAYS[p.code] ?? p.nom }))} />
              </div>
              <div>
                <p className="block text-xs font-bold text-dark uppercase tracking-wide mb-2">{t("operateur")}</p>
                <Select label={t("operateurMM")} value={operateur} onChange={setOperateur}
                  options={operateurs.map((o) => ({ value: o.code, label: o.nom }))} />
                {erreurs.operateur && <p className="text-xs text-red-600 mt-1.5 ml-1">{erreurs.operateur}</p>}
              </div>
            </div>
            <FormField
              label={t("numero", { indicatif: infos?.indicatif ?? "" })} id="remb-numero" inputMode="numeric" autoComplete="tel-national"
              value={numero} onChange={(e) => setNumero(e.target.value)} error={erreurs.numero}
              placeholder={infos ? "0".repeat(infos.chiffres) : ""} hint={infos ? t("chiffres", { nombre: infos.chiffres }) : undefined} required
            />
            {erreurs.general && <p role="alert" className="text-sm text-red-700 bg-red-50 rounded-xl p-3">{erreurs.general}</p>}
            <button type="submit" disabled={envoi} className="w-full bg-secondary hover:bg-secondary-600 text-white font-bold py-3.5 rounded-2xl disabled:opacity-60">
              {envoi ? t("enregistrement") : t("recevoir")}
            </button>
            <button type="button" onClick={onClose} className="w-full text-sm font-semibold text-gray-600 py-2 hover:text-dark">
              {t("plusTard")}
            </button>
          </form>
        )}
      </div>
    </div>,
    document.body,
  );
}
