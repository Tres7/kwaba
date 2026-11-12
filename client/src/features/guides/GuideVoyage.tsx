import { Fragment } from "react";
import {
  Banknote, Car, Compass, ExternalLink, Handshake, House, IdCard, PlaneLanding, PlugZap, ShieldCheck, Smartphone, Sun,
  Syringe, TriangleAlert, type LucideIcon,
} from "lucide-react";
import { Link } from "@/i18n/navigation";
import PageHero from "@/components/layout/PageHero";
import { filtrerLiens, type ReglagesSite } from "@/lib/modules";
import { RUBRIQUES, type GuidePays, type IconeRubrique } from "./types";

const ICONES: Record<IconeRubrique, LucideIcon> = {
  passeport: IdCard, sante: Syringe, argent: Banknote, avion: PlaneLanding, deplacements: Car, telephone: Smartphone,
  climat: Sun, prise: PlugZap, logement: House, securite: ShieldCheck, usages: Handshake,
};

/** "a **word** to remember" → the word in bold. */
function Texte({ texte }: { texte: string }) {
  return (
    <>
      {texte.split("**").map((morceau, i) => (i % 2 ? <strong key={i} className="font-semibold text-dark">{morceau}</strong> : <Fragment key={i}>{morceau}</Fragment>))}
    </>
  );
}

/** "Prepare your trip" page of a country: the same headings for every country, rendered on the server. */
export default function GuideVoyage({ guide, modules }: { guide: GuidePays; modules?: ReglagesSite["modules"] }) {
  return (
    <>
      <PageHero surtitre={<><Compass size={16} aria-hidden /> {guide.nom}</>} titre={guide.titre} sousTitre={guide.intro} />
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8 md:py-12">
        <p className="flex items-start gap-2 rounded-2xl bg-amber-50 text-amber-900 px-4 py-3 text-sm mb-8">
          <TriangleAlert size={18} className="shrink-0 mt-0.5" aria-hidden />
          <span><strong className="font-semibold">{guide.misAJour}.</strong> {guide.avertissement}</span>
        </p>
        <div className="grid grid-cols-1 lg:grid-cols-[220px_1fr] gap-8">
          <nav aria-label={guide.sommaire} className="hidden lg:block">
            <div className="sticky top-28">
              <p className="text-xs font-bold uppercase tracking-wider text-muted mb-3">{guide.sommaire}</p>
              <ol className="space-y-1.5 text-sm">
                {RUBRIQUES.map((cle) => (
                  <li key={cle}><a href={`#${cle}`} className="text-gray-600 hover:text-primary">{guide.rubriques[cle].titre}</a></li>
                ))}
              </ol>
            </div>
          </nav>
          <div className="space-y-5">
            {RUBRIQUES.map((cle) => {
              const r = guide.rubriques[cle];
              const Icone = ICONES[r.icone];
              const action = r.action && filtrerLiens([r.action], modules)[0];
              return (
                <section key={cle} id={cle} className="scroll-mt-28 bg-white rounded-2xl shadow-card p-5 sm:p-6">
                  <h2 className="flex items-center gap-3 font-heading font-bold text-dark text-xl">
                    <span className="h-10 w-10 rounded-xl bg-primary-50 text-primary flex items-center justify-center shrink-0">
                      <Icone size={20} aria-hidden />
                    </span>
                    {r.titre}
                  </h2>
                  <ul className="mt-4 space-y-2.5 text-gray-700 leading-relaxed list-disc pl-5 marker:text-accent">
                    {r.points.map((point) => <li key={point}><Texte texte={point} /></li>)}
                  </ul>
                  {r.sources && (
                    <p className="mt-4 text-sm text-muted">
                      {guide.sourcesTitre} :{" "}
                      {r.sources.map((s, i) => (
                        <Fragment key={s.url}>
                          {i > 0 && " · "}
                          <a href={s.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-primary font-medium hover:underline">
                            {s.libelle} <ExternalLink size={13} aria-hidden />
                          </a>
                        </Fragment>
                      ))}
                    </p>
                  )}
                  {action && (
                    <Link href={action.href}
                      className="mt-5 inline-flex items-center gap-2 rounded-xl bg-primary text-white text-sm font-bold px-5 py-3 hover:bg-primary-700 transition-colors">
                      {action.libelle}
                    </Link>
                  )}
                </section>
              );
            })}
          </div>
        </div>
      </div>
    </>
  );
}
