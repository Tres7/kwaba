"use client";

import { Link } from "@/i18n/navigation";
import { useMemo, useState } from "react";
import { Search, ChevronDown, Mail, MessageCircle } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import SubPageHeader from "@/components/layout/SubPageHeader";
import FormulaireReclamation from "@/components/aide/FormulaireReclamation";
import { CONTACT_EMAIL } from "@/lib/contact";
import { SECTIONS_EN } from "./faq-en";

// Réponses rédigées à partir des CGV et des CGU (audit n° 3) : chacune renvoie à son article. Les réponses marquées
// « hors CGV/CGU » décrivent le fonctionnement du site et ne figurent dans aucun des deux textes.
const SECTIONS = [
  {
    id: "reservations",
    title: "Réservations",
    items: [
      { q: "Comment réserver un hébergement ?", a: "Choisissez vos dates et le nombre de voyageurs sur la fiche, puis « Réserver ». Avant de payer, vous voyez un récapitulatif complet : prix détaillé en F CFA, politique d'annulation, règles de l'annonce (CGV, art. 5.1). Vous acceptez les CGV en cochant une case, puis vous payez. La réservation est ferme dès la confirmation du paiement (art. 5.2 et 5.3)." },
      { q: "Puis-je réserver si le logement est déjà pris ?", a: "Non. Une fois une réservation confirmée, ses dates sont bloquées chez le prestataire, qui refuse d'autres clients pour ces dates (CGV, art. 10.2). La recherche avec dates n'affiche donc que les logements libres sur la période." },
      { q: "Comment contacter mon hôte ?", a: "Par la messagerie de Kwa-Ba, avant comme après le paiement (CGV, art. 5.4) : bouton « Contacter » sur la fiche, puis « Messages ». Les échanges restent courtois et liés au séjour (CGU, art. 6.1). Ne réglez jamais l'hôte hors de la Plateforme : vous perdriez la Garantie Kwa-Ba (CGU, art. 6.2)." },
    ],
  },
  {
    id: "annulation",
    title: "Annulation",
    items: [
      { q: "Comment annuler une réservation ?", a: "Depuis Profil → Mes réservations, bouton « Annuler ». L'heure retenue est celle enregistrée par la Plateforme, à l'heure de Lomé (CGV, art. 11.2). Le remboursement suit la politique choisie par l'hôte (Souple, Modérée ou Ferme), affichée sur l'annonce (annexe 1). Annulée dans les 48 heures suivant la confirmation et au moins 7 jours avant l'arrivée, elle est remboursée en entier, frais de service compris (art. 10.3)." },
      { q: "Puis-je annuler un séjour commencé ?", a: "Un départ anticipé ne donne droit à aucun remboursement, sauf accord de l'hôte ou application de la Garantie Kwa-Ba (CGV, art. 9.3). Si le logement est très différent de l'annonce, insalubre, dangereux ou inaccessible, signalez-le dans les 24 heures suivant l'arrivée, photos à l'appui : Kwa-Ba vous reloge ou rembourse les nuits non consommées (art. 12)." },
    ],
  },
  {
    id: "paiement",
    title: "Paiement",
    items: [
      { q: "Quels moyens de paiement sont acceptés ?", a: "Le paiement passe par FedaPay, établissement agréé par la BCEAO : Mobile Money (Moov Money/Flooz, Mixx by Yas/T-Money) ou carte Visa ou Mastercard (CGV, art. 7.1). Le prix est toujours payé en F CFA (art. 7.3) ; un affichage en euros n'est qu'un équivalent indicatif. Ne payez jamais un prestataire en espèces, sauf le dépôt de garantie d'un logement remis contre reçu (art. 7.5)." },
      { q: "Quand suis-je débité ?", a: "Au moment où vous réservez, sur la page sécurisée de FedaPay ; Kwa-Ba ne conserve pas les données complètes de votre carte (CGV, art. 7.1). La réservation est ferme dès la confirmation du paiement ; la confirmation vous est envoyée aussitôt, et au plus tard sous cinq jours (art. 5.3). Le prix ne peut plus augmenter ensuite (art. 6.2)." },
      { q: "Quand l'hôte est-il payé ?", a: "Kwa-Ba conserve le prix jusqu'à 24 heures après votre arrivée, puis le verse à l'hôte (CGV, art. 8.1). Ce délai vous permet de signaler un problème avant que l'hôte ne soit payé (art. 8.3)." },
      { q: "Comment suis-je remboursé ?", a: "Sur le moyen de paiement d'origine, dans un délai de sept jours ouvrés ; à défaut, sur un compte Mobile Money à votre nom, avec votre accord (CGV, art. 11.5). Le montant dépend de la politique d'annulation de l'annonce (annexe 1). Si le prestataire annule, vous êtes remboursé intégralement, frais de service compris (art. 11.3)." },
      { q: "Que comprennent les frais de service ?", a: "Ils rémunèrent le service de réservation et l'assistance de Kwa-Ba (CGV, art. 2 et 3.3). Ils s'élèvent à 6 % du prix des nuits ; 3 % pour un client fidèle qui revient chez le même hôte ou pour un Pack Séjour + Chauffeur (art. 6.4). Les réductions ne se cumulent pas, et le détail est affiché avant le paiement (art. 5.1)." },
    ],
  },
  {
    id: "transferts",
    title: "Transfert aéroport",
    items: [
      { q: "Comment réserver un chauffeur à l'aéroport ?", a: "Depuis « Transfert aéroport » : indiquez votre vol, le nombre de passagers et de bagages, choisissez le véhicule, puis payez. Le prix est forfaitaire par trajet, selon l'aéroport et la catégorie de véhicule, chauffeur compris, le même de jour comme de nuit (CGV, art. 6.5)." },
      { q: "Quand vais-je connaître mon chauffeur ?", a: "Le nom et le numéro du chauffeur vous sont communiqués après son attribution, au plus tard 24 heures avant la prise en charge (CGV, art. 5.4). Si le chauffeur est absent ou a plus d'une heure de retard, Kwa-Ba cherche un remplaçant ou rembourse le trajet (art. 12)." },
      { q: "Mon vol a du retard : que faire ?", a: "Prévenez le chauffeur dès que possible, au numéro communiqué avec votre transfert (CGV, art. 5.4). L'attente au-delà d'une heure peut être facturée en heures supplémentaires, 1 000 F CFA l'heure (annexe 1 et art. 6.5). Un simple retard de vol ne donne pas droit au remboursement pour circonstances exceptionnelles (art. 11.4)." },
      { q: "Puis-je annuler ?", a: "Oui : un transfert annulé jusqu'à 24 heures avant est remboursé en entier ; moins de 24 heures avant, il ne l'est plus (CGV, annexe 1). Le délai de réflexion s'applique aussi : annulation dans les 48 heures suivant la réservation et au moins 7 jours avant le trajet, remboursement intégral (art. 10.3)." },
    ],
  },
  {
    id: "compte",
    title: "Mon compte",
    items: [
      // Hors CGV/CGU : fonctionnement du site
      { q: "Je n'ai pas reçu mon code de vérification", a: "Vérifiez vos spams, puis utilisez « Renvoyer le code » sur la page de vérification (un nouveau code toutes les 60 secondes). Le code est valable 10 minutes." },
      { q: "J'ai oublié mon mot de passe", a: "Cliquez sur « Mot de passe oublié ? » sur la page de connexion : un code vous est envoyé par email pour choisir un nouveau mot de passe. Gardez vos identifiants confidentiels et prévenez Kwa-Ba en cas d'usage frauduleux (CGU, art. 4.3)." },
      { q: "Comment devenir hôte ?", a: "Depuis « Devenir hôte », activez votre compte hôte puis préparez votre annonce dans l'Espace hôte. Seul un partenaire inscrit, qui a accepté les conditions qui le concernent, peut publier (CGU, art. 5.1). Avant publication, Kwa-Ba vérifie votre identité et vos documents, et visite le logement (art. 5.2). L'annonce doit être exacte et ne contenir aucune coordonnée personnelle (art. 5.3 et 5.4)." },
      { q: "Comment changer de langue ?", a: "Utilisez le sélecteur FR / EN en haut de la page ou dans le pied de page, ou Profil → Langue & région ; votre choix est mémorisé sur cet appareil. Les CGV sont rédigées en français, qui fait foi en cas de traduction (CGV, art. 1.4)." },
    ],
  },
  {
    id: "conditions",
    title: "Conditions d'utilisation",
    items: [
      { q: "Engagements des voyageurs", a: "Réserver avec un compte exact, à votre nom, en étant majeur (CGU, art. 4.2 ; CGV, art. 4.1). Respecter les règles de l'annonce : horaires, nombre de personnes, bruit, fêtes, visiteurs (CGV, art. 13.1), et présenter une pièce d'identité si l'hôte la demande (art. 13.2). Tout paiement passe par la Plateforme (art. 7.5)." },
      { q: "Engagements des hôtes", a: "Décrire l'offre de façon exacte et complète : photos récentes, équipements, règles, prix en F CFA, conditions d'annulation (CGU, art. 5.3). Ne mettre aucune coordonnée permettant de traiter hors de la Plateforme (art. 5.4). L'hôte reste responsable de sa prestation et de sa conformité à l'annonce (CGV, art. 3.2)." },
    ],
  },
  {
    id: "confidentialite",
    title: "Confidentialité",
    items: [
      { q: "Quelles données sont collectées ?", a: "Celles de votre compte (nom, prénom, email, téléphone, pays de résidence : CGU, art. 4.2), vos réservations, paiements et messages, traités selon la loi n° 2019-014 et la politique de confidentialité (CGU, art. 13.1). Seules les données nécessaires à la prestation sont transmises au prestataire (CGV, art. 20.2). Vous pouvez y accéder, les rectifier ou les faire supprimer (art. 20.3)." },
      // Hors CGV/CGU : fonctionnement du site
      { q: "Mon mot de passe est-il protégé ?", a: "Oui : il est stocké sous forme chiffrée (hachée) et n'est jamais visible, y compris par l'équipe Kwa-Ba." },
    ],
  },
  {
    id: "reclamations",
    title: "Réclamations",
    items: [
      { q: "Comment faire une réclamation ?", a: "Par le formulaire en bas de cette page ou par email : Kwa-Ba en accuse réception sous 72 heures (CGV, art. 21.1). En cas de désaccord avec un prestataire, Kwa-Ba propose une médiation gratuite et rend un avis écrit sous 10 jours (art. 21.2). Une solution amiable est recherchée pendant 30 jours avant toute action en justice (art. 21.3)." },
    ],
  },
];

export default function HelpPage() {
  const t = useTranslations("aide");
  const sections = useLocale() === "en" ? SECTIONS_EN : SECTIONS;
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState<string | null>(null);

  const filtered = useMemo(() => {
    const term = query.trim().toLowerCase();
    if (!term) return sections;
    return sections.map((s) => ({ ...s, items: s.items.filter((i) => `${i.q} ${i.a}`.toLowerCase().includes(term)) })).filter((s) => s.items.length);
  }, [query, sections]);

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8 md:py-12">
      <SubPageHeader title={t("titre")} subtitle={t("sousTitre")} />

      <div className="relative mb-8">
        <Search size={20} className="absolute left-5 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          type="search" value={query} onChange={(e) => setQuery(e.target.value)}
          placeholder={t("rechercher")}
          className="w-full bg-white rounded-full py-4 pl-14 pr-6 border border-gray-200 shadow-sm focus:outline-none focus:ring-4 focus:ring-primary/10 text-base sm:text-[15px]"
        />
      </div>

      <div className="space-y-8">
        {filtered.length === 0 && <p className="text-center text-gray-500 py-8">{t("aucunResultat", { recherche: query })}</p>}
        {filtered.map((section) => (
          <section key={section.id} id={section.id} className="scroll-mt-28">
            <h2 className="font-heading font-bold text-lg text-dark mb-3">{section.title}</h2>
            <div className="bg-white rounded-2xl border border-gray-100 shadow-sm divide-y divide-gray-100 overflow-hidden">
              {section.items.map((item) => {
                const key = `${section.id}-${item.q}`;
                const isOpen = open === key || !!query;
                return (
                  <div key={key}>
                    <button onClick={() => setOpen(isOpen && !query ? null : key)} aria-expanded={isOpen} className="w-full flex items-center justify-between gap-4 p-4 sm:p-5 text-left hover:bg-gray-50">
                      <span className="font-medium text-dark text-sm sm:text-[15px]">{item.q}</span>
                      <ChevronDown size={18} className={`text-muted flex-shrink-0 transition-transform ${isOpen ? "rotate-180" : ""}`} />
                    </button>
                    {isOpen && <p className="px-4 sm:px-5 pb-5 text-sm text-gray-600 leading-relaxed">{item.a}</p>}
                  </div>
                );
              })}
            </div>
          </section>
        ))}
      </div>

      <div className="mt-10 bg-white rounded-2xl border border-gray-100 p-6 flex flex-col sm:flex-row items-start sm:items-center gap-4">
        <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center text-primary flex-shrink-0"><MessageCircle size={22} /></div>
        <div className="flex-1">
          <p className="font-bold text-dark">{t("questionSejour")}</p>
          <p className="text-sm text-muted">{t("questionSejourTexte")}</p>
        </div>
        <Link href="/messages" className="bg-dark text-white font-medium px-5 py-3 rounded-xl hover:bg-black">{t("mesMessages")}</Link>
      </div>

      <section id="contact" className="mt-10 scroll-mt-28 bg-white rounded-2xl border border-gray-100 p-6">
        <h2 className="font-heading font-bold text-lg text-dark">{t("contactTitre")}</h2>
        <p className="text-sm text-muted mt-1">{t("contactTexte")}</p>
        <ul className="mt-4 grid sm:grid-cols-2 gap-3 text-sm">
          <li className="flex items-center gap-3 rounded-xl bg-gray-50 px-4 py-3">
            <Mail size={18} className="text-primary flex-shrink-0" />
            <a href={`mailto:${CONTACT_EMAIL}`} className="font-semibold text-dark hover:text-primary">{CONTACT_EMAIL}</a>
          </li>
        </ul>
        <h3 className="font-heading font-bold text-dark mt-8 mb-1">{t("reclamationTitre")}</h3>
        <p className="text-sm text-muted mb-4">{t("reclamationTexte")}</p>
        <FormulaireReclamation />
      </section>
    </div>
  );
}
