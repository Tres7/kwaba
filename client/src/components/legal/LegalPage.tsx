import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";

export interface SectionLegale {
  id: string;
  titre: string;
  contenu: React.ReactNode;
  /** Number shown before the title (by default, the section's rank); "" for an appendix. */
  numero?: string;
}

interface LegalPageProps {
  titre: string;
  miseAJour: string;
  intro: React.ReactNode;
  sections: SectionLegale[];
}

const PAGES = [
  { href: "/mentions-legales", cle: "mentions" },
  { href: "/cgu", cle: "cgu" },
  { href: "/cgv", cle: "cgv" },
  { href: "/confidentialite", cle: "confidentialite" },
  { href: "/cookies", cle: "cookies" },
  { href: "/remboursement", cle: "remboursement" },
];

/** Template of the legal pages: table of contents, anchored sections, links between documents. */
export default function LegalPage({ titre, miseAJour, intro, sections }: LegalPageProps) {
  const t = useTranslations("legal");
  return (
    <div className="bg-light">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-10 md:py-14 lg:grid lg:grid-cols-[16rem_1fr] lg:gap-12">
        <aside className="hidden lg:block">
          <nav aria-label={t("documents")} className="sticky top-28 space-y-1 text-sm">
            <p className="font-heading font-bold text-dark mb-3">{t("informations")}</p>
            {PAGES.map((p) => (
              <Link key={p.href} href={p.href} className="block px-3 py-2 rounded-lg text-gray-600 hover:bg-white hover:text-dark">{t(`titres.${p.cle}`)}</Link>
            ))}
          </nav>
        </aside>

        <article className="bg-white rounded-3xl shadow-card p-6 sm:p-10 min-w-0">
          <h1 className="font-heading font-bold text-3xl sm:text-4xl text-dark">{titre}</h1>
          <p className="text-sm text-gray-600 mt-2">{t("miseAJour", { date: miseAJour })}</p>
          <div className="mt-6 text-gray-700 leading-relaxed space-y-3">{intro}</div>

          <nav aria-label={t("sommaire")} className="mt-8 p-5 rounded-2xl bg-gray-50">
            <p className="font-semibold text-dark text-sm mb-2">{t("sommaire")}</p>
            <ol className="list-decimal list-inside space-y-1 text-sm">
              {sections.map((s) => (
                <li key={s.id} className={s.numero === "" ? "list-none" : undefined}><a href={`#${s.id}`} className="text-primary hover:underline">{s.titre}</a></li>
              ))}
            </ol>
          </nav>

          {sections.map((s, i) => (
            <section key={s.id} id={s.id} className="mt-10 scroll-mt-28" aria-labelledby={`${s.id}-titre`}>
              <h2 id={`${s.id}-titre`} className="font-heading font-bold text-xl text-dark mb-3">{s.numero === "" ? "" : `${s.numero ?? i + 1}. `}{s.titre}</h2>
              <div className="text-gray-700 leading-relaxed space-y-3 [&_ul]:list-disc [&_ul]:pl-5 [&_ul]:space-y-1 [&_a]:text-primary [&_a]:underline [&_table]:w-full [&_table]:text-sm [&_th]:text-left [&_th]:p-2 [&_th]:bg-gray-50 [&_td]:p-2 [&_td]:align-top [&_tr]:border-b [&_tr]:border-gray-100">
                {s.contenu}
              </div>
            </section>
          ))}
        </article>
      </div>
    </div>
  );
}

/** In English: reminder that the French version is authoritative (to put in the introduction). */
export function VersionFrancaiseFaitFoi() {
  return (
    <p className="text-sm bg-gray-50 rounded-xl p-3">
      This English version is provided for convenience. In case of any difference, the French version prevails.
    </p>
  );
}

/**
 * Information to be provided by the company before going live (identity, contacts, hosting provider…).
 * Deliberately visible: no legal data is made up.
 */
export function AC({ children }: { children: React.ReactNode }) {
  const t = useTranslations("legal");
  return <mark className="bg-amber-100 text-amber-900 px-1 rounded font-semibold">[{t("aCompleter")} : {children}]</mark>;
}
