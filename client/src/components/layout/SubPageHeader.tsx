import { Link } from "@/i18n/navigation";
import { ArrowLeft } from "lucide-react";
import { useTranslations } from "next-intl";

export default function SubPageHeader({ title, subtitle, back = "/profil" }: { title: string; subtitle?: string; back?: string }) {
  const t = useTranslations("commun");
  return (
    <div className="mb-8 flex items-center gap-4">
      <Link href={back} aria-label={t("retour")} className="w-10 h-10 rounded-full bg-surface shadow-xs flex items-center justify-center text-dark hover:bg-light-muted transition-colors shrink-0">
        <ArrowLeft size={20} />
      </Link>
      <div>
        <h1 className="font-heading font-bold text-2xl sm:text-3xl text-dark">{title}</h1>
        {subtitle && <p className="text-muted text-sm mt-1">{subtitle}</p>}
      </div>
    </div>
  );
}
