"use client";

import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { CreditCard, Lock, Smartphone, Wallet } from "lucide-react";
import SubPageHeader from "@/components/layout/SubPageHeader";
import { useConfigPaiement, useOperateursMobileMoney } from "@/features/paiements";

const METHODS = [
  { icon: Smartphone, id: "mobileMoney" },
  { icon: CreditCard, id: "carte" },
  { icon: Wallet, id: "paypal" },
];

export default function PaymentMethodsPage() {
  const t = useTranslations("moyensPaiement");
  const operateurs = useOperateursMobileMoney();
  // PayPal only shows if the API offers it (payment methods not open at launch)
  const paypal = useConfigPaiement().data?.moyens.includes("paypal") ?? false;
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8 md:py-12">
      <SubPageHeader title={t("titre")} subtitle={t("sousTitre")} />

      <div className="bg-white rounded-3xl shadow-card p-5 sm:p-8 space-y-4">
        {METHODS.filter((m) => m.id !== "paypal" || paypal).map(({ icon: Icon, id }) => (
          <div key={id} className="flex items-center gap-4 p-4 rounded-2xl border border-gray-100">
            <div className="w-12 h-12 rounded-xl bg-primary/10 text-primary flex items-center justify-center flex-shrink-0"><Icon size={22} /></div>
            <div>
              <p className="font-bold text-dark">{t(`moyens.${id}.titre`)}</p>
              <p className="text-sm text-muted">{t(`moyens.${id}.texte`, { operateurs })}</p>
            </div>
          </div>
        ))}

        <p className="flex items-start gap-3 text-sm text-gray-600 bg-gray-50 rounded-2xl p-4">
          <Lock size={18} className="text-secondary flex-shrink-0 mt-0.5" />
          <span>
            {t(paypal ? "securitePaypal" : "securite")}{" "}
            <Link href="/remboursement" className="text-primary font-semibold hover:underline">{t("enSavoirPlus")}</Link>
          </span>
        </p>
      </div>
    </div>
  );
}
