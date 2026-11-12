import { useTranslations } from "next-intl";
import { Mail, MessageCircle, ShieldCheck } from "lucide-react";
import SubPageHeader from "@/components/layout/SubPageHeader";

const ITEMS = [
  { icon: ShieldCheck, id: "securite" },
  { icon: Mail, id: "bienvenue" },
  { icon: MessageCircle, id: "messages" },
];

export default function NotificationsPage() {
  const t = useTranslations("notifications");
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8 md:py-12">
      <SubPageHeader title={t("titre")} subtitle={t("sousTitre")} />

      <div className="bg-white rounded-3xl shadow-card p-5 sm:p-8 space-y-4">
        {ITEMS.map(({ icon: Icon, id }) => (
          <div key={id} className="flex items-start gap-4 p-4 rounded-2xl border border-gray-100">
            <div className="w-11 h-11 bg-primary/10 rounded-xl flex items-center justify-center text-primary shrink-0"><Icon size={20} /></div>
            <div className="flex-1 min-w-0">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="font-bold text-dark">{t(`elements.${id}.titre`)}</p>
                <span className="text-xs font-semibold text-muted bg-gray-100 px-2.5 py-1 rounded-full">{t(`elements.${id}.canal`)}</span>
              </div>
              <p className="text-sm text-muted mt-1">{t(`elements.${id}.texte`)}</p>
            </div>
          </div>
        ))}
        <p className="text-sm text-gray-500 pt-2">{t("aucunePub")}</p>
      </div>
    </div>
  );
}
