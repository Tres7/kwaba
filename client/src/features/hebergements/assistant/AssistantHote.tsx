"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { ArrowLeft, ArrowRight, Check, CloudOff, Loader2 } from "lucide-react";
import { toast } from "sonner";
import Logo from "@/components/layout/Logo";
import { useRouter } from "@/i18n/navigation";
import { apiErrorMessage } from "@/lib/api";
import { cn } from "@/lib/utils";
import { lireConditions, soumettreBrouillon } from "../api";
import type { DonneesAnnonce } from "../brouillons";
import { clesHebergements } from "../hooks";
import Decor, { Tuile } from "./Decor";
import { ECRANS } from "./Ecrans";
import { PICTOS_PHASES, etapeAffichee, etapeVoisine, peutContinuer, progressionPhases, type CleEtape, type Etape } from "./etapes";
import { useBrouillonAssistant, type EtatSauvegarde } from "./useBrouillonAssistant";

function Sauvegarde({ etat }: { etat: EtatSauvegarde }) {
  const t = useTranslations("assistantHote.etat");
  const [Icone, texte] = etat === "en_cours" ? [Loader2, t("enCours")] : etat === "hors_ligne" ? [CloudOff, t("horsLigne")] : [Check, t("enregistre")];
  return (
    <p role="status" className={cn("flex items-center gap-1.5 text-xs", etat === "hors_ligne" ? "text-amber-700 font-semibold" : "text-gray-500")}>
      <Icone size={14} className={cn(etat === "en_cours" && "animate-spin")} aria-hidden /> <span className="hidden sm:inline">{texte}</span>
    </p>
  );
}

/** Three segments, one per phase: shows at a glance what is left, not a percentage to reach. */
function Progression({ cle }: { cle: CleEtape }) {
  const t = useTranslations("assistantHote");
  const parts = progressionPhases(cle);
  const total = Math.round((parts.reduce((a, b) => a + b, 0) / parts.length) * 100);
  return (
    <div role="progressbar" aria-label={t("progression")} aria-valuenow={total} aria-valuemin={0} aria-valuemax={100} className="flex gap-1.5">
      {parts.map((part, i) => (
        <span key={i} className="flex-1 h-1.5 rounded-full bg-gray-200 overflow-hidden">
          <span className="block h-full rounded-full bg-primary transition-[width] duration-500 ease-out" style={{ width: `${part * 100}%` }} />
        </span>
      ))}
    </div>
  );
}

/** What travellers will see, building up as the host answers. */
function Apercu({ donnees }: { donnees: DonneesAnnonce }) {
  const { name, city, location, image_url: couverture } = donnees;
  if (!name && !couverture) return null;
  return (
    <div className="absolute bottom-8 left-8 right-8 max-w-sm hidden lg:flex items-center gap-3 rounded-2xl bg-white/90 backdrop-blur-sm p-3 shadow-lg">
      {couverture && <img src={couverture} alt="" className="w-16 h-16 rounded-xl object-cover shrink-0" />}
      <div className="min-w-0">
        <p className="font-heading font-bold text-dark truncate">{name}</p>
        <p className="text-xs text-gray-500 truncate">{[location, city].filter(Boolean).join(", ")}</p>
      </div>
    </div>
  );
}

function Intro({ cle }: { cle: CleEtape }) {
  const t = useTranslations("assistantHote");
  if (cle === "bienvenue") {
    return (
      <>
        <h1 className="font-heading font-bold text-dark text-3xl sm:text-4xl leading-tight sm:leading-10">{t("bienvenue.titre")}</h1>
        <p className="text-gray-600 mt-3">{t("bienvenue.texte")}</p>
        <ol className="mt-7 space-y-5">
          {([1, 2, 3] as const).map((phase) => (
            <li key={phase} className="flex items-center gap-4">
              <Tuile picto={PICTOS_PHASES[phase]} phase={phase} className="w-14 h-14 shrink-0 shadow-none" />
              <div>
                <p className="font-heading font-bold text-dark">{phase}. {t(`phases.${phase}.titre`)}</p>
                <p className="text-sm text-gray-500">{t(`phases.${phase}.texte`)}</p>
              </div>
            </li>
          ))}
        </ol>
      </>
    );
  }
  return (
    <>
      {t.has(`${cle}.surtitre`) && <p className="text-sm font-bold uppercase tracking-wide text-secondary">{t(`${cle}.surtitre`)}</p>}
      <h1 className="font-heading font-bold text-dark text-3xl sm:text-4xl leading-tight sm:leading-10 mt-2">{t(`${cle}.titre`)}</h1>
      <p className="text-gray-600 text-lg mt-4">{t(`${cle}.texte`)}</p>
    </>
  );
}

function Parcours({ id, etape, donnees, assistant }: {
  id: string; etape: Etape; donnees: DonneesAnnonce; assistant: ReturnType<typeof useBrouillonAssistant>;
}) {
  const t = useTranslations("assistantHote");
  const router = useRouter();
  const queryClient = useQueryClient();
  const [occupe, setOccupe] = useState(false);
  const [sens, setSens] = useState<"avant" | "arriere">("avant");
  const [envoi, setEnvoi] = useState(false);
  // Read again while the host is on a screen that changes it: identity document sent, payout account saved…
  const { data: conditions } = useQuery({
    queryKey: clesHebergements.conditions(id), queryFn: () => lireConditions(id), enabled: etape.phase === 3 && !envoi,
    refetchOnMount: "always", refetchInterval: etape.fait ? 3000 : false,
  });
  const Ecran = ECRANS[etape.cle];
  const suivante = etapeVoisine(etape, 1, conditions, donnees);
  const precedente = etapeVoisine(etape, -1, conditions, donnees);
  const pret = peutContinuer(etape, donnees, assistant.erreurs, conditions) && !occupe && !envoi;

  const aller = (cible: Etape, direction: "avant" | "arriere") => {
    setSens(direction);
    window.scrollTo({ top: 0 });
    void assistant.envoyer(cible.cle);
    router.push(`/hote/annonce/${id}?etape=${cible.cle}`, { scroll: false });
  };

  /** Saved before leaving: the host space reads the draft from the API. */
  const quitter = async (destination: string) => {
    await assistant.envoyer(etape.cle);
    queryClient.removeQueries({ queryKey: clesHebergements.brouillons, exact: true });
    router.push(destination);
  };

  /** The API checks everything again: the wizard only guides the host up to here. */
  const envoyer = async () => {
    setEnvoi(true);
    try {
      await assistant.envoyer(etape.cle);
      await soumettreBrouillon(id);
      queryClient.removeQueries({ queryKey: clesHebergements.brouillons });
      await queryClient.invalidateQueries({ queryKey: clesHebergements.mes });
      router.replace("/hote/annonce/envoyee");
    } catch (err) {
      toast.error(apiErrorMessage(err));
      setEnvoi(false);
    }
  };

  const continuer = () => {
    if (etape.cle === "recapitulatif") void envoyer();
    else if (suivante) aller(suivante, "avant");
  };

  return (
    <div className="min-h-dvh lg:h-dvh flex flex-col lg:flex-row bg-light-muted">
      <aside aria-hidden className={cn(
        "relative flex items-center justify-center overflow-hidden shrink-0 lg:flex-1 lg:h-full px-6 pt-4 lg:p-10",
        // The welcome screen has the three phases to show below its image
        etape.cle === "bienvenue" ? "h-[26dvh]" : etape.intro ? "h-[44dvh]" : etape.sansVisuelMobile ? "h-0 lg:h-full" : "h-[24dvh]",
      )}>
        <Decor key={etape.cle} picto={etape.picto} phase={etape.phase} grand={etape.intro} />
        {etape.phase >= 2 && <Apercu donnees={donnees} />}
      </aside>

      <div className={cn(
        "relative z-10 flex-1 lg:flex-none lg:w-[54%] xl:w-[50%] min-h-0 flex flex-col bg-white",
        "rounded-t-[2rem] lg:rounded-t-none lg:rounded-l-[2.5rem] shadow-[0_-12px_40px_rgba(14,77,71,0.08)]",
        !etape.sansVisuelMobile && "-mt-6 lg:mt-0",
      )}>
        <header className="flex items-center justify-between gap-3 px-5 sm:px-10 pt-5 pb-3">
          <Logo />
          <div className="flex items-center gap-4">
            <Sauvegarde etat={assistant.etat} />
            <button type="button" onClick={() => quitter("/hote/espace")}
              className="text-sm font-semibold text-dark underline underline-offset-4 decoration-gray-300 hover:decoration-primary">
              {t("quitter")}
            </button>
          </div>
        </header>

        <main id="contenu" className="flex-1 lg:overflow-y-auto px-5 sm:px-10 py-5 lg:py-8">
          <div key={etape.cle} data-sens={sens} className="assistant-entree max-w-xl mx-auto">
            {Ecran
              ? <Ecran donnees={donnees} modifier={assistant.modifier} erreurs={assistant.erreurs} onOccupe={setOccupe} conditions={conditions} />
              : <Intro cle={etape.cle} />}
          </div>
        </main>

        <footer className="sticky bottom-0 bg-white px-5 sm:px-10 pt-3 pb-[max(1rem,env(safe-area-inset-bottom))] border-t border-gray-100">
          <Progression cle={etape.cle} />
          <div className="flex items-center justify-between gap-3 mt-3">
            <button type="button" onClick={() => precedente && aller(precedente, "arriere")} disabled={!precedente}
              className="inline-flex items-center gap-1.5 px-2 py-3 text-sm font-semibold text-dark disabled:invisible">
              <ArrowLeft size={18} aria-hidden /> {t("retour")}
            </button>
            <button type="button" onClick={continuer} disabled={!pret}
              className="inline-flex items-center gap-2 whitespace-nowrap px-5 sm:px-7 py-3.5 rounded-2xl bg-primary text-white font-bold shadow-button transition-all hover:bg-primary-600 motion-safe:active:scale-[0.98] disabled:opacity-40 disabled:shadow-none">
              {occupe ? t("envoiPhotos") : envoi ? t("envoi") : t(etape.cle === "bienvenue" ? "commencer" : etape.cle === "recapitulatif" ? "envoyer" : "suivant")}
              <ArrowRight size={18} aria-hidden />
            </button>
          </div>
        </footer>
      </div>
    </div>
  );
}

/** "Become a host" wizard: one question per screen, saved as the host goes. The address gives the screen (?etape=). */
export default function AssistantHote({ id }: { id: string }) {
  const router = useRouter();
  const demandee = useSearchParams().get("etape");
  const assistant = useBrouillonAssistant(id);
  const { donnees, etapeEnregistree, introuvable } = assistant;

  useEffect(() => {
    if (introuvable) router.replace("/hote/espace");
  }, [introuvable, router]);

  if (!donnees) return <div className="min-h-dvh bg-light-muted" />;
  const etape = etapeAffichee(demandee ?? etapeEnregistree, donnees);
  return <Parcours id={id} etape={etape} donnees={donnees} assistant={assistant} />;
}
