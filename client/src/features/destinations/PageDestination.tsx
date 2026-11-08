import { getTranslations } from "next-intl/server";
import { ArrowRight, ChevronRight, Compass, Home, MapPin, ShieldCheck } from "lucide-react";
import { Link } from "@/i18n/navigation";
import type { Langue } from "@/i18n/routing";
import PageHero from "@/components/layout/PageHero";
import JsonLd from "@/components/seo/JsonLd";
import { cheminPays, cheminQuartier, cheminVille, logementsDu, villesDuPays } from "@/lib/destinations";
import { filAriane, listeLogements } from "@/lib/donnees-structurees";
import { filtrerLiens, type ReglagesSite } from "@/lib/modules";
import { lireApi } from "@/lib/seo";
import { cn } from "@/lib/utils";
import ListeLogements from "./ListeLogements";
import { GUIDES, lireExperiences, lireLogements, textesDestination, type Destination } from "./destination";

interface Lieu {
  nom: string;
  chemin: string;
  nombre: number;
}

const puce = "inline-flex items-center gap-1.5 rounded-full border border-gray-200 bg-white px-4 py-2 text-sm font-semibold text-dark hover:border-primary/40 hover:text-primary transition-colors";

/**
 * Country, city or district page: its listings rendered by the server (what Google reads), the places under it,
 * ideas of things to do and the other cities. The search page stays the place to filter by dates and price.
 */
export default async function PageDestination({ locale, destination }: { locale: Langue; destination: Destination }) {
  const { pays, ville, quartier } = destination;
  const [t, tous, reglages] = await Promise.all([
    getTranslations({ locale, namespace: "destinations" }),
    lireLogements(),
    lireApi<ReglagesSite>("/v1/site/", 300),
  ]);
  const experiences = ville && !quartier ? await lireExperiences(ville, reglages?.modules) : [];
  const { nomPays, lieu, titre, intro } = textesDestination(t, destination);
  const logements = logementsDu(tous, destination);

  const etapes = [
    { nom: t("accueil"), chemin: "/" },
    { nom: nomPays, chemin: cheminPays(pays) },
    ...(ville ? [{ nom: ville.nom, chemin: cheminVille(ville) }] : []),
    ...(ville && quartier ? [{ nom: quartier, chemin: cheminQuartier(ville, quartier) }] : []),
  ];

  // Country: all its cities. City: its districts that have listings. District: the other districts of the city
  const sousLieux: Lieu[] = !ville
    ? villesDuPays(pays).map((v) => ({ nom: v.nom, chemin: cheminVille(v), nombre: logementsDu(tous, { pays, ville: v }).length }))
    : ville.quartiers
      .filter((q) => q !== quartier)
      .map((q) => ({ nom: q, chemin: cheminQuartier(ville, q), nombre: logementsDu(tous, { pays, ville, quartier: q }).length }))
      .filter((l) => l.nombre > 0);
  const autresVilles = ville ? villesDuPays(pays).filter((v) => v !== ville) : [];

  const recherche = quartier ?? ville?.nom;
  const lienRecherche = recherche ? `/recherche?city=${encodeURIComponent(recherche)}` : "/recherche";
  const guide = GUIDES[pays];
  const lienDecouvrir = ville && filtrerLiens([{ href: `/decouvrir?ville=${encodeURIComponent(experiences[0]?.ville ?? ville.nom)}` }], reglages?.modules)[0];

  return (
    <>
      <JsonLd donnees={[filAriane(locale, etapes), ...(logements.length ? [listeLogements(locale, logements)] : [])]} />
      <PageHero
        large
        surtitre={<><MapPin size={16} aria-hidden /> {ville ? `${quartier ? `${quartier}, ` : ""}${ville.nom}, ${nomPays}` : nomPays}</>}
        titre={titre}
        sousTitre={intro}
        image={logements.find((h) => h.image_url)?.image_url}
      >
        <p className="mt-5 inline-flex items-center gap-2 rounded-full bg-white/15 px-4 py-2 text-sm font-semibold">
          <Home size={15} aria-hidden /> {t("nombre", { nombre: logements.length })}
        </p>
      </PageHero>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 md:py-10 space-y-10 md:space-y-12">
        <nav aria-label={t("filAriane")}>
          <ol className="flex flex-wrap items-center gap-1 text-sm text-gray-500">
            {etapes.map((e, i) => (
              <li key={e.chemin} className="flex items-center gap-1">
                {i > 0 && <ChevronRight size={14} aria-hidden />}
                {i === etapes.length - 1
                  ? <span aria-current="page" className="font-semibold text-dark">{e.nom}</span>
                  : <Link href={e.chemin} className="hover:text-primary hover:underline">{e.nom}</Link>}
              </li>
            ))}
          </ol>
        </nav>

        {sousLieux.length > 0 && (
          <section aria-labelledby="sous-lieux">
            <h2 id="sous-lieux" className="font-heading font-bold text-dark text-xl md:text-2xl mb-4">
              {ville ? (quartier ? t("autresQuartiers", { ville: ville.nom }) : t("quartiers")) : t("titreVilles")}
            </h2>
            <ul className="flex flex-wrap gap-2">
              {sousLieux.map((l) => (
                <li key={l.chemin}>
                  <Link href={l.chemin} className={puce}>
                    {l.nom} <span className="font-normal text-gray-500">{t("nombreCourt", { nombre: l.nombre })}</span>
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        )}

        <section aria-labelledby="logements">
          <div className="flex flex-wrap items-end justify-between gap-3 mb-5">
            <h2 id="logements" className="font-heading font-bold text-dark text-xl md:text-2xl">{t("logements", { lieu })}</h2>
            {logements.length > 0 && (
              <Link href={lienRecherche} className="inline-flex items-center gap-1 text-sm font-bold text-primary hover:underline">
                {t("filtrer")} <ArrowRight size={15} aria-hidden />
              </Link>
            )}
          </div>
          {logements.length > 0 ? (
            <ListeLogements logements={logements} />
          ) : (
            <div className="rounded-2xl bg-white shadow-card p-6 md:p-8 max-w-2xl">
              <p className="font-heading font-bold text-dark text-lg">{t("vide", { lieu })}</p>
              <p className="text-gray-600 mt-2">{t("videTexte")}</p>
              <div className="mt-5 flex flex-wrap gap-3">
                <Link href="/recherche" className="rounded-xl bg-primary px-5 py-3 text-sm font-bold text-white hover:bg-primary-700 transition-colors">{t("voirTous")}</Link>
                <Link href="/hote" className="rounded-xl border border-primary/30 px-5 py-3 text-sm font-bold text-primary hover:bg-primary/5 transition-colors">{t("proposer")}</Link>
              </div>
            </div>
          )}
          <p className="mt-5 flex items-start gap-2 text-sm text-gray-600 max-w-3xl">
            <ShieldCheck size={18} className="text-primary flex-shrink-0 mt-0.5" aria-hidden /> {t("confiance")}
          </p>
        </section>

        {ville && experiences.length > 0 && (
          <section aria-labelledby="a-faire">
            <h2 id="a-faire" className="font-heading font-bold text-dark text-xl md:text-2xl mb-4">{t("aFaire", { ville: ville.nom })}</h2>
            <ul className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {experiences.slice(0, 8).map((e) => (
                <li key={e.id} className="rounded-2xl bg-white shadow-card p-4">
                  <p className="font-semibold text-dark">{(locale === "en" && e.nom_en) || e.nom}</p>
                  <p className="text-sm text-gray-500 mt-0.5">{(locale === "en" && e.etiquette_en) || e.etiquette}</p>
                </li>
              ))}
            </ul>
            {lienDecouvrir && (
              <Link href={lienDecouvrir.href} className="mt-4 inline-flex items-center gap-1 text-sm font-bold text-primary hover:underline">
                <Compass size={15} aria-hidden /> {t("voirExperiences", { ville: ville.nom })}
              </Link>
            )}
          </section>
        )}

        {(autresVilles.length > 0 || guide) && (
          <section className="border-t border-gray-100 pt-8">
            {autresVilles.length > 0 && (
              <>
                <h2 id="autres-villes" className="font-heading font-bold text-dark text-lg mb-3">{t("autresVilles", { dans: t(`pays.${pays}.dans`) })}</h2>
                <ul className="flex flex-wrap gap-2">
                  {autresVilles.map((v) => (
                    <li key={v.nom}><Link href={cheminVille(v)} className={cn(puce, "font-medium")}>{v.nom}</Link></li>
                  ))}
                </ul>
              </>
            )}
            {guide && (
              <Link href={guide} className="mt-5 inline-flex items-center gap-1 text-sm font-bold text-primary hover:underline">
                {t(`pays.${pays}.guide`)} <ArrowRight size={15} aria-hidden />
              </Link>
            )}
          </section>
        )}
      </div>
    </>
  );
}
