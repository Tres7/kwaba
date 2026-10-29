import { Link } from "@/i18n/navigation";
import LienContact from "@/components/legal/LienContact";
import MentionSociete from "@/components/legal/MentionSociete";
import LegalPage, { AC } from "@/components/legal/LegalPage";

/** Numbered paragraph of an article ("6.1. …"). */
function N({ n, children }: { n: string; children: React.ReactNode }) {
  return <p><strong>{n}.</strong> {children}</p>;
}

/** French version (authoritative). Terms of sale version 2.4 of 18 October 2026, adapted to the open services. */
export default function ContenuFr() {
  return (
    <LegalPage
      titre="Conditions générales de vente"
      miseAJour="23 octobre 2026"
      intro={
        <>
          <p>
            Le site kwa-ba.com et ses applications (la « Plateforme ») sont exploités par <strong>KWA-BA SARL</strong>, société à
            responsabilité limitée au capital de 100 000 F CFA, dont le siège est situé quartier Totsi Gblenkomé, rue 243, Lomé (Togo),
            immatriculée au RCCM de Lomé sous le numéro <MentionSociete cle="rccm" libelle="RCCM" />, NIF <MentionSociete cle="nif" libelle="NIF" />, enregistrée comme prestataire de commerce
            électronique sous le numéro <MentionSociete cle="commerce_electronique" libelle="numéro d&apos;enregistrement" />, représentée par ses cogérants, M. MENDE Fadel et M. KPOGLO Dzidoula Godwin Trésor.
          </p>
          <ul className="list-disc pl-5 space-y-1">
            <li>Contact : <LienContact sujet="Conditions générales de vente" /> ; adresse postale : quartier Totsi Gblenkomé, rue 243, Lomé, Togo.</li>
            <li>Cogérants : M. MENDE Fadel et M. KPOGLO Dzidoula Godwin Trésor — Directeur de la publication : M. MENDE Fadel.</li>
          </ul>
          <p>
            Les présentes conditions générales de vente (les « CGV ») complètent les <Link href="/cgu">conditions générales d’utilisation</Link> (les
            « CGU ») et la <Link href="/confidentialite">politique de confidentialité</Link> de la Plateforme.
          </p>
        </>
      }
      sections={[
        {
          id: "objet",
          titre: "Objet et champ d’application",
          contenu: (
            <>
              <N n="1.1">Les CGV s’appliquent à toute réservation ou commande passée sur la Plateforme par un client. Elles portent sur les services suivants :</N>
              <ul>
                <li>hébergement de courte durée (hôtels, appartements et maisons meublés) ;</li>
                <li>mobilité : transferts depuis ou vers l’aéroport, voiture avec chauffeur, voiture sans chauffeur, chauffeur pour le véhicule du client.</li>
              </ul>
              <N n="1.2">Les services ouverts plus tard (location de longue durée, Loyer Sécurisé, Lien Kwa-Ba Direct, Kwa-Ba Pro, excursions, contrat cadre entreprises, billetterie Kwa-Ba Events) sont régis par des conditions particulières qui complètent les CGV, publiées à leur ouverture.</N>
              <N n="1.3">En cas de contradiction, l’ordre de priorité est le suivant : 1) les conditions particulières de l’annonce ou du service, affichées avant la réservation ; 2) les CGV ; 3) les CGU. Une condition particulière de l’annonce ne peut jamais réduire les droits que les CGV ou la loi donnent au client. Une telle condition est réputée non écrite.</N>
              <N n="1.4">Les CGV sont rédigées en français, qui fait foi en cas de traduction.</N>
            </>
          ),
        },
        {
          id: "definitions",
          titre: "Définitions",
          contenu: (
            <table>
              <thead><tr><th>Terme</th><th>Sens</th></tr></thead>
              <tbody>
                <tr><td>Client</td><td>Toute personne qui réserve ou commande un service : voyageur, entreprise</td></tr>
                <tr><td>Consommateur</td><td>Client personne physique qui agit à des fins qui n’entrent pas dans son activité professionnelle</td></tr>
                <tr><td>Professionnel</td><td>Client qui agit pour les besoins de son activité (entreprise, ONG, administration)</td></tr>
                <tr><td>Prestataire</td><td>Celui qui fournit le service réservé : hôte, hôtel, propriétaire de véhicule, chauffeur</td></tr>
                <tr><td>Partenaire</td><td>Membre du Réseau Kwa-Ba Partenaires : démarcheur, apporteur, relais, hôte, propriétaire, chauffeur</td></tr>
                <tr><td>Annonce</td><td>La page qui décrit le service, son prix, ses règles, sa politique d’annulation et, le cas échéant, son dépôt de garantie</td></tr>
                <tr><td>Prix</td><td>Le prix fixé par le prestataire (nuits, véhicule)</td></tr>
                <tr><td>Frais de service</td><td>La rémunération de KWA-BA payée par le client pour son service de réservation</td></tr>
                <tr><td>Prix total</td><td>Le montant total affiché avant le paiement : prix, frais de service, prix du chauffeur, taxes éventuelles</td></tr>
                <tr><td>Dépôt de garantie</td><td>La somme remise en garantie et restituée en fin de prestation (souvent appelée « caution »)</td></tr>
                <tr><td>Garantie Kwa-Ba</td><td>Les engagements de KWA-BA décrits à l’article 12</td></tr>
              </tbody>
            </table>
          ),
        },
        {
          id: "role",
          titre: "Rôle de KWA-BA",
          contenu: (
            <>
              <N n="3.1">KWA-BA agit comme <strong>intermédiaire de commerce</strong>. Elle met en relation le client et le prestataire, présente les annonces, organise la réservation et, selon le service, encaisse le paiement pour le compte du prestataire.</N>
              <N n="3.2">Le contrat de séjour, de location de véhicule ou de transport est conclu <strong>directement entre le client et le prestataire</strong>. Le prestataire est responsable de sa prestation, de sa conformité à l’annonce et du respect des règles qui s’appliquent à son activité : autorisations, assurances, déclarations fiscales, registre des voyageurs.</N>
              <N n="3.3">KWA-BA fournit en son nom propre : le service de réservation et l’assistance (frais de service) ; la part KWA-BA du prix du chauffeur ; la Garantie Kwa-Ba. Elle répond de ces services dans les conditions de l’article 19.</N>
              <N n="3.4">KWA-BA vérifie chaque annonce avant publication : visite du logement, contrôle des papiers du véhicule (carte grise, visite technique, assurance) et du chauffeur (permis, casier judiciaire ou attestation). Cette vérification réduit les risques sans pouvoir garantir l’absence de tout défaut.</N>
              <N n="3.5">KWA-BA n’est ni hôtelier, ni loueur de véhicules, ni transporteur, ni agent immobilier titulaire d’un mandat de gestion, ni organisateur d’événements, ni assureur.</N>
            </>
          ),
        },
        {
          id: "compte",
          titre: "Accès au service et compte",
          contenu: (
            <>
              <N n="4.1">Pour réserver, le client doit être <strong>majeur</strong> et capable de contracter, et disposer d’un compte personnel exact et à jour. Il est responsable de la confidentialité de ses identifiants.</N>
              <N n="4.2">Une personne mineure ne peut séjourner dans un logement réservé par la Plateforme qu’accompagnée d’un parent ou d’un adulte responsable muni d’une autorisation. À défaut, le prestataire refuse l’accès ; la réservation est alors annulée sans remboursement, et les faits peuvent être signalés aux autorités.</N>
              <N n="4.3">KWA-BA peut demander une pièce d’identité ou d’autres justificatifs avant une réservation, notamment pour une location de véhicule sans chauffeur. Une réservation dont les justificatifs ne sont pas fournis peut être annulée avec remboursement intégral.</N>
              <N n="4.4">KWA-BA peut annuler une réservation, avec remboursement intégral, en cas de soupçon sérieux de fraude, d’usurpation d’identité, de paiement contesté ou de risque pour la sécurité. Elle en informe le client.</N>
            </>
          ),
        },
        {
          id: "etapes",
          titre: "Étapes de la réservation",
          contenu: (
            <>
              <N n="5.1">Avant de payer, le client voit un récapitulatif complet : le service réservé ; les dates et horaires ; le nombre de personnes ; le prix total en F CFA, détaillé ; la politique d’annulation ; l’existence ou non d’un droit de rétractation et ses modalités ; le dépôt de garantie éventuel ; les règles de l’annonce. Il peut corriger ses choix ou abandonner à tout moment.</N>
              <N n="5.2">Le client accepte expressément les CGV, les règles de l’annonce et la politique d’annulation en cochant une case avant de payer. Ces documents sont consultables, téléchargeables et imprimables.</N>
              <N n="5.3">La réservation est ferme dès la confirmation du paiement. KWA-BA envoie une confirmation par courriel aussitôt après la confirmation du paiement, et au plus tard sous cinq jours. Elle contient le récapitulatif et le lien vers les CGV. Un reçu électronique est délivré pour chaque paiement.</N>
              <N n="5.4">Les échanges avec le prestataire passent par la messagerie de la Plateforme, avant comme après le paiement. Pour une mission de mobilité, le nom et le numéro du chauffeur sont communiqués au client après l’attribution, au plus tard 24 heures avant la mission.</N>
              <N n="5.5"><strong>Demande de réservation :</strong> lorsque l’annonce le prévoit, le prestataire dispose de 24 heures pour accepter. Sans réponse, la demande est annulée et le montant éventuellement prélevé est remboursé intégralement.</N>
            </>
          ),
        },
        {
          id: "prix",
          titre: "Prix et frais",
          contenu: (
            <>
              <N n="6.1">Les prix sont exprimés en <strong>francs CFA, toutes taxes comprises</strong>. Le prix total affiché avant le paiement est celui que paie le client. <AC>régime de TVA de KWA-BA</AC></N>
              <N n="6.2">Le prix est fixé à la réservation. Il ne peut pas être augmenté ensuite, sauf demande du client (prolongation, personne supplémentaire, option).</N>
              <N n="6.3"><strong>Erreur manifeste de prix :</strong> si un prix affiché est grossièrement erroné (par exemple 1 000 F CFA la nuit au lieu de 100 000), KWA-BA ou le prestataire peut annuler la réservation en remboursant intégralement le client. Aucun supplément ne peut lui être réclamé.</N>
              <p className="font-semibold text-dark">6.4. Hébergement de courte durée</p>
              <table>
                <thead><tr><th>Élément</th><th>Montant</th></tr></thead>
                <tbody>
                  <tr><td>Prix des nuits, frais de ménage éventuels</td><td>Fixés par l’hôte ou l’hôtel, affichés avant la réservation</td></tr>
                  <tr><td>Frais de service du client</td><td><strong>6 %</strong> du prix des nuits</td></tr>
                  <tr><td>Pack Séjour + Chauffeur (logement réservé avec une voiture avec chauffeur)</td><td>3 % sur le logement</td></tr>
                  <tr><td>Client sous contrat cadre entreprise</td><td>4 %</td></tr>
                  <tr><td>Client fidèle (nouveau séjour chez le même hôte par la Plateforme)</td><td>3 %</td></tr>
                  <tr><td>Taxe de séjour ou taxe locale, si elle est applicable</td><td>Indiquée sur l’annonce et incluse dans le prix total</td></tr>
                </tbody>
              </table>
              <p>Les réductions ne se cumulent pas : le taux le plus bas s’applique.</p>
              <p className="font-semibold text-dark">6.5. Mobilité</p>
              <table>
                <thead><tr><th>Élément</th><th>Montant</th></tr></thead>
                <tbody>
                  <tr><td>Prix du véhicule (par jour)</td><td>Fixé par le propriétaire ; <strong>aucun frais de service</strong> pour le client</td></tr>
                  <tr><td>Transfert depuis ou vers l’aéroport</td><td>Prix forfaitaire par trajet affiché par la Plateforme selon l’aéroport et la catégorie de véhicule, <strong>chauffeur compris</strong></td></tr>
                  <tr><td>Chauffeur (voiture avec chauffeur, chauffeur seul)</td><td><strong>7 000 F CFA par jour</strong> de 10 heures au plus</td></tr>
                  <tr><td>Heure supplémentaire du chauffeur</td><td>1 000 F CFA</td></tr>
                  <tr><td>Prime de déplacement du chauffeur</td><td>1 500 F CFA par jour dans le pays hors de Lomé ; 2 000 F CFA par jour hors du pays</td></tr>
                  <tr><td>Carburant, péages, stationnement</td><td>À la charge du client, sauf mention contraire de l’annonce</td></tr>
                  <tr><td>Logement et repas du chauffeur en cas de nuitée hors de Lomé</td><td>Selon ce qui est indiqué à la réservation</td></tr>
                  <tr><td>Kilométrage</td><td>Illimité, sauf limite indiquée sur l’annonce et prix du kilomètre supplémentaire</td></tr>
                  <tr><td>Dépôt de garantie (sans chauffeur uniquement)</td><td>Article 14</td></tr>
                </tbody>
              </table>
            </>
          ),
        },
        {
          id: "paiement",
          titre: "Paiement",
          contenu: (
            <>
              <N n="7.1">Les paiements sont traités par <strong>FedaPay</strong>, établissement de paiement agréé par la BCEAO : Mobile Money (Moov Money, Mixx by Yas et autres opérateurs proposés) et carte bancaire (Visa, Mastercard). PayPal peut être proposé en complément, lorsqu’il est indiqué au moment du paiement. KWA-BA peut recourir à un autre prestataire de paiement agréé, notamment si FedaPay est indisponible. KWA-BA ne conserve pas les données complètes des cartes bancaires.</N>
              <N n="7.2">Selon le service, le prix est soit encaissé par KWA-BA pour le compte du prestataire, en vertu du mandat donné par celui-ci (le paiement fait à KWA-BA vaut alors paiement au prestataire), soit réglé au prestataire par l’intermédiaire de la Plateforme. Le mode applicable est indiqué au moment du paiement.</N>
              <N n="7.3">Le prix est toujours payé en F CFA. Pour une carte émise hors de la zone franc, la conversion est faite par la banque du client, à son taux. Si PayPal est proposé, le montant en euros est affiché avant validation (parité fixe 1 € = 655,957 F CFA). Les frais éventuels de la banque du client restent à sa charge.</N>
              <N n="7.4">Les frais des prestataires de paiement sont pris en charge par KWA-BA, sauf mention contraire affichée avant le paiement.</N>
              <N n="7.5"><strong>Paiement hors Plateforme interdit.</strong> Aucun paiement ne doit être fait au prestataire, au chauffeur ou à un démarcheur en espèces ou par tout autre moyen pour une prestation réservée par la Plateforme. Seul fait exception le dépôt de garantie d’un logement remis à l’hôte contre reçu (article 13.5). Un paiement direct en dehors de ce cas n’est pas couvert par la Garantie Kwa-Ba.</N>
              <N n="7.6"><strong>Contestation de paiement :</strong> un client qui conteste auprès de sa banque ou de son opérateur un paiement pour une prestation fournie s’expose à la suspension de son compte et au recouvrement des sommes dues. Il est invité à contacter d’abord KWA-BA (article 21).</N>
            </>
          ),
        },
        {
          id: "versement",
          titre: "Versement au prestataire",
          contenu: (
            <>
              <N n="8.1">Hébergement : le prix est conservé jusqu’à <strong>24 heures après l’arrivée</strong> du client, puis versé à l’hôte.</N>
              <N n="8.2">Mobilité : le prix est versé au prestataire après le début de la mission ou de la location ; pour une location avec dépôt de garantie, après le délai de signalement des dommages (article 14.3).</N>
              <N n="8.3">Ces délais permettent au client de signaler un problème avant que le prestataire ne soit payé.</N>
            </>
          ),
        },
        {
          id: "modification",
          titre: "Modification et prolongation",
          contenu: (
            <>
              <N n="9.1">Toute modification (dates, nombre de personnes, durée) se demande par la Plateforme. Elle n’est acquise qu’après l’accord du prestataire et le paiement de l’éventuelle différence.</N>
              <N n="9.2">Une prolongation de séjour ou de location doit être réservée et payée par la Plateforme avant la fin de la prestation en cours.</N>
              <N n="9.3">Un départ anticipé ou une restitution anticipée du véhicule ne donne droit à aucun remboursement, sauf accord du prestataire ou application de la Garantie Kwa-Ba.</N>
            </>
          ),
        },
        {
          id: "retractation",
          titre: "Droit de rétractation du consommateur",
          contenu: (
            <>
              <N n="10.1">Conformément à la loi n° 2017-07 relative aux transactions électroniques (art. 44), le consommateur peut se rétracter sans motif dans un délai de <strong>dix jours ouvrables</strong> à compter de la conclusion du contrat. Il notifie sa rétractation depuis son espace de réservation ou par courriel. Les sommes versées lui sont remboursées dans les 10 jours suivant cette notification (art. 46). Ce délai de rétractation ne se confond pas avec le délai de remboursement après une annulation, qui est de sept jours ouvrés (article 11.5).</N>
              <N n="10.2">Ce droit ne peut plus être exercé lorsque l’exécution du service a commencé avec l’accord du consommateur avant la fin de ce délai (art. 47). En confirmant une réservation pour des dates déterminées, le consommateur demande expressément que le service de réservation soit exécuté immédiatement : les dates sont bloquées chez le prestataire, qui refuse d’autres clients pour ces dates. Il reconnaît qu’il ne pourra plus alors exercer son droit de rétractation sur ces dates, et que la politique d’annulation de l’annexe 1 s’applique.</N>
              <N n="10.3"><strong>Délai de réflexion offert :</strong> même lorsque le droit de rétractation ne s’applique pas, toute réservation de courte durée ou de mobilité annulée dans les <strong>48 heures</strong> suivant sa confirmation, et au moins <strong>7 jours</strong> avant l’arrivée ou la prise du véhicule, est remboursée intégralement, frais de service compris.</N>
              <N n="10.4">Les clients professionnels ne bénéficient pas du droit de rétractation (art. 43 de la même loi).</N>
            </>
          ),
        },
        {
          id: "annulation",
          titre: "Annulation et remboursement",
          contenu: (
            <>
              <N n="11.1">Les règles d’annulation de chaque service figurent à l’<a href="#annexe-1">annexe 1</a> et sur la page <Link href="/remboursement">Annulation et remboursement</Link>. Celle qui s’applique est affichée sur l’annonce et dans le récapitulatif avant le paiement.</N>
              <N n="11.2">Le client annule depuis son espace de réservation. L’heure de l’annulation est celle enregistrée par la Plateforme, à l’heure de Lomé (GMT).</N>
              <N n="11.3"><strong>Annulation par le prestataire :</strong> le client est remboursé intégralement, frais de service compris, et KWA-BA l’aide à trouver une solution équivalente (article 12).</N>
              <N n="11.4"><strong>Circonstances exceptionnelles :</strong> le client est remboursé intégralement, frais de service compris, si la prestation devient impossible ou interdite pour l’un des motifs suivants, survenu après la réservation et justifié : catastrophe naturelle ; épidémie déclarée par les autorités avec des restrictions de déplacement ; fermeture des frontières ; interdiction officielle de voyager ; couvre-feu ou troubles graves dans la zone ; décès ou hospitalisation grave du client ou d’un proche parent, sur justificatif. À la place du remboursement, le client peut choisir un avoir. Ne sont pas couverts : les retards ou annulations de vol ordinaires, les difficultés de visa connues à la réservation, les maladies sans hospitalisation, et les événements connus à la date de la réservation.</N>
              <N n="11.5">Les remboursements sont faits sur le moyen de paiement d’origine, dans un délai de <strong>sept jours ouvrés</strong>. Ce délai concerne les remboursements après annulation ; il est distinct du délai de rétractation de dix jours ouvrables (article 10.1). Si ce n’est pas possible, ils sont faits sur un compte Mobile Money au nom du client, avec son accord. En cas d’indisponibilité du prestataire de paiement, KWA-BA informe le client et rembourse dès le rétablissement du service ou par un autre moyen, dans le respect des délais fixés par la loi.</N>
            </>
          ),
        },
        {
          id: "garantie",
          titre: "Garantie Kwa-Ba",
          contenu: (
            <>
              <table>
                <thead><tr><th>Situation</th><th>Engagement de KWA-BA</th><th>Condition</th></tr></thead>
                <tbody>
                  <tr><td>Logement très différent de l’annonce, insalubre, dangereux ou inaccessible</td><td>Relogement équivalent ou remboursement des nuits non consommées et des frais de service</td><td>Signalement dans les <strong>24 heures suivant l’arrivée</strong>, photos à l’appui</td></tr>
                  <tr><td>Problème important survenu pendant le séjour (eau, électricité, sécurité, équipement essentiel annoncé) non réglé par l’hôte sous 24 heures</td><td>Remboursement proportionnel des nuits concernées, ou relogement</td><td>Signalement dans les 24 heures suivant sa découverte</td></tr>
                  <tr><td>Annulation par l’hôte, logement déjà occupé (surréservation)</td><td>Relogement équivalent ou remboursement intégral</td><td>–</td></tr>
                  <tr><td>Chauffeur ou véhicule absent, en retard de plus d’une heure ou empêché</td><td>Recherche d’un remplaçant ; à défaut, remboursement de la journée ou du trajet</td><td>Signalement immédiat</td></tr>
                  <tr><td>Véhicule différent de l’annonce ou en mauvais état</td><td>Remplacement ou remboursement</td><td>Signalement avant le départ, photos à l’appui</td></tr>
                  <tr><td>Désaccord sur un dépôt de garantie</td><td>Arbitrage de KWA-BA sur pièces (articles 13 et 14)</td><td>Signalement dans les 7 jours</td></tr>
                </tbody>
              </table>
              <p>La Garantie Kwa-Ba ne couvre pas : les différences de goût ou d’appréciation ; les incidents causés par le client ; les prestations ou paiements faits en dehors de la Plateforme ; les objets personnels perdus ou volés ; les dommages indirects (vols manqués, autres réservations).</p>
              <p>Le remboursement accordé à ce titre est plafonné au prix total de la réservation concernée, sauf disposition légale contraire.</p>
            </>
          ),
        },
        {
          id: "sejour",
          titre: "Règles du séjour",
          contenu: (
            <>
              <N n="13.1">Le client respecte les règles de l’annonce : heures d’arrivée et de départ ; nombre maximal de personnes ; animaux ; tabac ; bruit ; fêtes et événements, interdits sauf autorisation écrite ; visiteurs. Toute personne non déclarée peut être refusée ou facturée selon l’annonce.</N>
              <N n="13.2">Le client présente une pièce d’identité au prestataire si celui-ci la demande pour le registre des voyageurs.</N>
              <N n="13.3">Un départ après l’heure prévue sans accord de l’hôte peut être facturé selon le barème indiqué sur l’annonce, dans la limite d’une nuit.</N>
              <N n="13.4"><strong>Activités illicites</strong> : prostitution, drogue, armes, accueil de mineurs non accompagnés, troubles graves. Elles entraînent la fin immédiate du séjour sans remboursement et peuvent être signalées aux autorités.</N>
              <N n="13.5"><strong>Dépôt de garantie pour un logement</strong> : l’hôte peut en demander un, à condition qu’il soit indiqué sur l’annonce avant la réservation. Il est limité à une nuit et à 50 000 F CFA au plus. Il est remis à l’arrivée contre un reçu et restitué au départ, ou au plus tard sous 48 heures. Si un dommage est déclaré selon l’article 13.6, l’hôte ne conserve que le montant correspondant, jusqu’à l’avis de KWA-BA. Aucun autre dépôt ne peut être exigé.</N>
              <N n="13.6"><strong>Dommages causés par le client.</strong> L’hôte déclare les dommages dans les <strong>48 heures</strong> suivant le départ, par la Plateforme, avec photos et devis ou facture. Le client dispose de <strong>72 heures</strong> pour répondre. À défaut d’accord, KWA-BA rend un avis motivé, en tenant compte de l’usure normale. Le montant retenu est d’abord prélevé sur le dépôt de garantie éventuel. Le solde est payé par le client sous 7 jours par la Plateforme ; à défaut, KWA-BA peut suspendre son compte et l’hôte conserve ses recours.</N>
            </>
          ),
        },
        {
          id: "mobilite",
          titre: "Règles de la mobilité",
          contenu: (
            <>
              <N n="14.1"><strong>Conducteur (sans chauffeur)</strong> : au moins <strong>23 ans</strong> ; permis de conduire obtenu depuis au moins <strong>2 ans</strong> et valable au Togo ; permis international ou traduction si la réglementation l’exige. Le propriétaire peut fixer des conditions plus strictes sur l’annonce. Seuls les conducteurs déclarés à la réservation peuvent conduire.</N>
              <N n="14.2"><strong>État des lieux</strong> : au départ et au retour, le client et le propriétaire photographient le véhicule (carrosserie, intérieur, compteur, niveau de carburant). Un défaut non noté au départ est présumé survenu pendant la location, sauf preuve contraire.</N>
              <N n="14.3"><strong>Dépôt de garantie (sans chauffeur uniquement)</strong> :</N>
              <ul>
                <li>le propriétaire choisit, à la publication, entre aucun dépôt (badge « Sans caution »), une journée de location ou deux journées, dans la limite de 100 000 F CFA ;</li>
                <li>le dépôt est divisé par deux pour un client qui a fait 3 locations sans incident ;</li>
                <li>il est <strong>payé en ligne avec la location et conservé par KWA-BA</strong> pendant la location ; le propriétaire n’en demande aucun à la remise des clés ;</li>
                <li>le propriétaire signale tout dommage, carburant manquant ou retard, photos à l’appui, dans les 24 heures suivant le retour du véhicule ; le dépôt, diminué des retenues, est remboursé au client <strong>dans les 48 heures</strong> suivant le retour ;</li>
                <li>seules peuvent être retenues les sommes prévues au barème affiché (carburant manquant, retard, nettoyage anormal, petits dommages) ou justifiées par l’état des lieux et un devis ;</li>
                <li>en cas de désaccord, KWA-BA arbitre, et peut retenir le montant contesté jusqu’au règlement du litige.</li>
              </ul>
              <p>Aucun dépôt n’est demandé pour une location avec chauffeur.</p>
              <N n="14.4"><strong>Carburant</strong> : le véhicule est rendu avec le même niveau qu’au départ. À défaut, le carburant manquant est facturé au prix à la pompe, avec un forfait de service de 2 000 F CFA.</N>
              <N n="14.5"><strong>Retard de restitution</strong> : tolérance de 30 minutes. Au-delà, chaque heure de retard est facturée 10 % du prix journalier ; au-delà de 3 heures, une journée entière est due. Le client prévient le propriétaire dès qu’il prévoit un retard.</N>
              <N n="14.6"><strong>Usages interdits</strong> : conduite sous l’emprise d’alcool ou de stupéfiants ; conducteur non déclaré ; sous-location ; transport de personnes ou de marchandises contre rémunération ; courses de vitesse et usage hors route non autorisé ; remorquage ; transport de produits dangereux ou illicites ; sortie du Togo sans accord écrit du propriétaire et sans assurance couvrant les pays visités (carte brune CEDEAO).</N>
              <N n="14.7"><strong>Amendes, péages et stationnement</strong> : ils sont à la charge du client pour toute la durée de la location sans chauffeur. Avec chauffeur, les infractions de conduite sont à la charge du chauffeur, sauf si elles résultent d’une demande du client.</N>
              <N n="14.8"><strong>Accident, panne, vol</strong> : le client prévient immédiatement le propriétaire et KWA-BA, et au plus tard dans les <strong>24 heures</strong> ; il établit un constat amiable ou fait constater les faits par la police ou la gendarmerie, et ne reconnaît pas seul sa responsabilité ; en cas de vol, il dépose plainte et remet les clés et les papiers ; en cas de panne non imputable au client, le propriétaire remplace le véhicule ou rembourse les jours non utilisés.</N>
              <N n="14.9"><strong>Assurance et responsabilité du client</strong> : le propriétaire doit assurer le véhicule pour la location (responsabilité civile obligatoire et, le cas échéant, dommages) et indiquer sur l’annonce la franchise restant à la charge du conducteur. En cas de dommage survenu pendant la location sans chauffeur, la responsabilité du client est limitée au montant de cette franchise, sauf faute grave : alcool, stupéfiants, conducteur non déclaré, usage interdit, ou absence de déclaration dans les 24 heures. En cas de faute grave, le client répond de l’intégralité du dommage.</N>
              <N n="14.10"><strong>Chauffeur</strong> : journée de 10 heures au plus, avec des pauses raisonnables ; le chauffeur peut refuser une demande contraire à la loi, à la sécurité ou au code de la route ; le client reste responsable de ses objets personnels. <strong>Chauffeur pour le véhicule du client</strong> : le client garantit que son véhicule est en règle (papiers, visite technique) et que son assurance couvre la conduite par un tiers ; à défaut, le chauffeur peut refuser la mission sans que le client soit remboursé.</N>
            </>
          ),
        },
        {
          id: "longue-duree",
          titre: "Location de longue durée",
          contenu: <p>La recherche d’un logement à louer en longue durée (visites, mise en relation, état des lieux) n’est pas encore ouverte. Ses conditions seront publiées à son ouverture.</p>,
        },
        {
          id: "plateforme",
          titre: "Réserver par la Plateforme",
          contenu: (
            <>
              <N n="16.1">Pour un nouveau séjour ou une nouvelle location auprès d’un prestataire découvert sur la Plateforme, le client réserve à nouveau par la Plateforme. Il bénéficie alors du tarif Client fidèle (3 %) ou de la fonction « Mon chauffeur », et conserve la Garantie Kwa-Ba. La fonction « Mon chauffeur » permet au client de redemander un chauffeur qu’il a déjà eu par la Plateforme : ce chauffeur reçoit alors 6 500 F CFA par jour au lieu de 6 000, et KWA-BA conserve 500 F CFA au lieu de 1 000. Le prix payé par le client ne change pas.</N>
              <N n="16.2">Le client qui reçoit une proposition de paiement ou de réservation hors de la Plateforme peut la signaler à KWA-BA. Un signalement vérifié est récompensé par 5 000 F CFA.</N>
            </>
          ),
        },
        {
          id: "avis",
          titre: "Avis",
          contenu: (
            <>
              <N n="17.1">Seuls les clients qui ont effectivement bénéficié d’une prestation peuvent publier un avis, dans les 14 jours suivant sa fin.</N>
              <N n="17.2">L’avis doit être honnête, personnel et respectueux. Les propos injurieux, diffamatoires, discriminatoires ou les données personnelles de tiers sont interdits.</N>
              <N n="17.3">KWA-BA modère les avis selon la <Link href="/cgu#avis">charte des avis des CGU</Link>. Elle ne publie pas d’avis rémunérés ou rédigés par le prestataire. Le prestataire dispose d’un droit de réponse.</N>
            </>
          ),
        },
        {
          id: "suspension",
          titre: "Suspension du compte",
          contenu: (
            <>
              <N n="18.1">KWA-BA peut suspendre un compte en cas de manquement grave aux CGV : fraude, paiement hors Plateforme, violence, dommages répétés, faux avis, activité illicite.</N>
              <N n="18.2">Sauf urgence liée à la sécurité ou à une fraude, le client est d’abord informé des faits et dispose de 7 jours pour s’expliquer.</N>
              <N n="18.3">La suspension ne remet pas en cause les réservations déjà payées, sauf en cas de fraude ou de risque pour la sécurité ; ces réservations sont alors annulées et remboursées, sous déduction des sommes dues par le client.</N>
            </>
          ),
        },
        {
          id: "responsabilite",
          titre: "Responsabilité",
          contenu: (
            <>
              <N n="19.1">KWA-BA répond de la bonne exécution de ses propres services (article 3.3), sous réserve des dispositions légales impératives applicables au commerce électronique.</N>
              <N n="19.2">Le prestataire répond de l’exécution de sa prestation. KWA-BA dispose d’un recours contre lui pour toute somme qu’elle aurait payée à sa place.</N>
              <N n="19.3">Sauf faute lourde ou intentionnelle de KWA-BA, dommage corporel ou disposition légale contraire, sa responsabilité au titre de son propre service est limitée au montant des frais de service perçus pour la réservation concernée. Ce plafond ne s’applique pas à la Garantie Kwa-Ba, qui suit ses propres règles.</N>
              <N n="19.4">Aucune partie n’est responsable d’un manquement dû à la force majeure, c’est-à-dire à un événement imprévisible, irrésistible et extérieur.</N>
              <N n="19.5">KWA-BA met en œuvre des moyens raisonnables pour assurer l’accès à la Plateforme, sans garantir une disponibilité permanente.</N>
            </>
          ),
        },
        {
          id: "donnees",
          titre: "Données personnelles",
          contenu: (
            <>
              <N n="20.1">KWA-BA traite les données du client conformément à la loi n° 2019-014 du 29 octobre 2019 relative à la protection des données à caractère personnel et à sa <Link href="/confidentialite">politique de confidentialité</Link>. Déclaration auprès de l’IPDCP n° <MentionSociete cle="ipdcp" libelle="numéro de déclaration" />.</N>
              <N n="20.2">Seules les données nécessaires à la prestation sont transmises au prestataire.</N>
              <N n="20.3">Le client dispose d’un droit d’accès, de rectification, d’opposition et de suppression, à exercer à l’adresse <LienContact sujet="Mes données personnelles" />. Il peut aussi saisir l’IPDCP.</N>
              <N n="20.4">Il peut s’opposer à tout moment, sans frais, à recevoir des messages commerciaux (loi n° 2017-07, art. 37), par le lien prévu dans chaque message ou depuis son compte.</N>
              <N n="20.5">Les données peuvent être hébergées ou consultées hors du Togo, notamment par les associés établis en France et par le prestataire de paiement (FedaPay, établi au Bénin), dans le respect des conditions de transfert prévues par la loi. Le prestataire de paiement traite les données de paiement sous sa propre responsabilité, pour les besoins du paiement et de la lutte contre la fraude.</N>
            </>
          ),
        },
        {
          id: "reclamations",
          titre: "Réclamations, médiation et litiges",
          contenu: (
            <>
              <N n="21.1">Toute réclamation est adressée à KWA-BA par la Plateforme ou à <LienContact sujet="Réclamation" />. KWA-BA en accuse réception sous 72 heures.</N>
              <N n="21.2">En cas de désaccord avec un prestataire, KWA-BA propose une médiation gratuite et donne un avis écrit sous 10 jours, au vu des pièces fournies par chacun.</N>
              <N n="21.3">Les parties recherchent une solution amiable pendant 30 jours avant toute action en justice, sauf urgence.</N>
            </>
          ),
        },
        {
          id: "preuve",
          titre: "Preuve et conservation",
          contenu: (
            <>
              <N n="22.1">Les données enregistrées par la Plateforme font foi entre les parties, sauf preuve contraire : réservations, paiements, messages, codes de mission, photos horodatées, reçus. Conformément à la loi n° 2017-07, l’écrit électronique a la même force probante que l’écrit papier.</N>
              <N n="22.2">KWA-BA conserve les contrats conclus par voie électronique pendant au moins 5 ans après leur exécution, ou plus longtemps lorsque la loi l’exige, et y donne accès au client sur demande.</N>
            </>
          ),
        },
        {
          id: "divers",
          titre: "Dispositions diverses",
          contenu: (
            <>
              <N n="23.1">KWA-BA peut modifier les CGV. La version applicable est celle acceptée lors de la réservation. Toute modification importante est annoncée au moins 30 jours à l’avance aux clients disposant d’un compte.</N>
              <N n="23.2">Si une clause est déclarée nulle, les autres restent applicables.</N>
              <N n="23.3">Le fait de ne pas se prévaloir d’une clause ne vaut pas renonciation à celle-ci.</N>
              <N n="23.4">Les communications entre les parties se font par la Plateforme ou par courriel, aux coordonnées du compte.</N>
            </>
          ),
        },
        {
          id: "droit",
          titre: "Droit applicable et juridiction",
          contenu: (
            <>
              <N n="24.1">Les présentes conditions sont soumises au droit togolais et aux actes uniformes de l’OHADA, sans priver le consommateur des dispositions impératives du pays où il réside.</N>
              <N n="24.2">À défaut de solution amiable, tout litige relève des juridictions compétentes de Lomé, notamment du tribunal de commerce de Lomé pour les clients professionnels.</N>
            </>
          ),
        },
        {
          id: "annexe-1",
          numero: "",
          titre: "Annexe 1 – Politique d’annulation et de remboursement",
          contenu: (
            <>
              <p>Le délai de réflexion offert de 48 heures (article 10.3) et les règles des articles 11.3 et 11.4 s’appliquent en plus des tableaux ci-dessous.</p>
              <p className="font-semibold text-dark">Hébergement de courte durée (l’hôte choisit l’une des trois options, affichée sur l’annonce)</p>
              <TableauHebergement />
              <ul>
                <li><strong>Séjours de 28 nuits ou plus :</strong> le premier mois n’est pas remboursable en cas d’annulation moins de 30 jours avant l’arrivée ; les mois suivants sont remboursés si le client prévient au moins 30 jours à l’avance.</li>
                <li><strong>Non-présentation sans annulation :</strong> aucun remboursement.</li>
                <li><strong>Frais de ménage :</strong> remboursés si le client n’est pas arrivé.</li>
                <li><strong>Hôtels :</strong> la politique propre de l’hôtel, affichée avant la réservation, s’applique si elle est plus favorable au client.</li>
              </ul>
              <p className="font-semibold text-dark">Mobilité</p>
              <TableauMobilite />
              <p>En cas d’annulation tardive, la part du chauffeur lui est versée. Si un vol est retardé, le client prévient le chauffeur ; l’attente au-delà d’une heure peut être facturée en heures supplémentaires.</p>
            </>
          ),
        },
        {
          id: "annexe-2",
          numero: "",
          titre: "Annexe 2 – Récapitulatif des tarifs client",
          contenu: (
            <table>
              <thead><tr><th>Service</th><th>Ce que paie le client</th></tr></thead>
              <tbody>
                <tr><td>Séjour de courte durée</td><td>Prix des nuits + 6 % (3 % en Pack Séjour ou en Client fidèle, 4 % pour les entreprises sous contrat cadre)</td></tr>
                <tr><td>Voiture</td><td>Prix fixé par le propriétaire, sans frais de service</td></tr>
                <tr><td>Transfert aéroport</td><td>Prix forfaitaire du trajet, chauffeur compris</td></tr>
                <tr><td>Chauffeur</td><td>7 000 F CFA par jour + primes éventuelles (1 500 ou 2 000 F CFA par jour) + heures supplémentaires (1 000 F CFA)</td></tr>
              </tbody>
            </table>
          ),
        },
      ]}
    />
  );
}

/** Cancellation scale for stays (appendix 1), also shown on the "Cancellation and refund" page. */
export function TableauHebergement() {
  return (
    <table>
      <thead><tr><th>Option</th><th>Annulation par le client</th><th>Remboursement</th></tr></thead>
      <tbody>
        <tr><td><strong>Souple</strong></td><td>Jusqu’à 24 heures avant l’arrivée</td><td>Intégral, frais de service compris</td></tr>
        <tr><td></td><td>Moins de 24 heures avant</td><td>Première nuit retenue, reste remboursé ; frais de service conservés</td></tr>
        <tr><td><strong>Modérée</strong></td><td>Jusqu’à 5 jours avant l’arrivée</td><td>Intégral, frais de service compris</td></tr>
        <tr><td></td><td>Entre 5 jours et 24 heures avant</td><td>50 % des nuits ; frais de service conservés</td></tr>
        <tr><td></td><td>Moins de 24 heures avant</td><td>Aucun remboursement</td></tr>
        <tr><td><strong>Ferme</strong></td><td>Jusqu’à 30 jours avant l’arrivée</td><td>Intégral, frais de service compris</td></tr>
        <tr><td></td><td>Entre 30 et 7 jours avant</td><td>50 % des nuits ; frais de service conservés</td></tr>
        <tr><td></td><td>Moins de 7 jours avant</td><td>Aucun remboursement</td></tr>
      </tbody>
    </table>
  );
}

/** Cancellation scale for mobility (appendix 1). */
export function TableauMobilite() {
  return (
    <table>
      <thead><tr><th>Service</th><th>Annulation par le client</th><th>Remboursement</th></tr></thead>
      <tbody>
        <tr><td>Transfert depuis ou vers l’aéroport</td><td>Jusqu’à 24 heures avant</td><td>Intégral</td></tr>
        <tr><td></td><td>Moins de 24 heures avant</td><td>Aucun remboursement</td></tr>
        <tr><td>Voiture avec ou sans chauffeur, chauffeur seul</td><td>Jusqu’à 48 heures avant</td><td>Intégral</td></tr>
        <tr><td></td><td>Entre 48 et 24 heures avant</td><td>50 %</td></tr>
        <tr><td></td><td>Moins de 24 heures avant</td><td>Aucun remboursement</td></tr>
      </tbody>
    </table>
  );
}
