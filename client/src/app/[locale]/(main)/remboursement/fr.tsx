import { Link } from "@/i18n/navigation";
import LienContact from "@/components/legal/LienContact";
import LegalPage from "@/components/legal/LegalPage";
import { TableauHebergement, TableauMobilite } from "../cgv/fr";

/** French version. Takes appendix 1 and articles 10 to 12 of the terms of sale. */
export default function ContenuFr() {
  return (
    <LegalPage
      titre="Politique d'annulation et de remboursement"
      miseAJour="22 octobre 2026"
      intro={
        <>
          <p>
            Cette page explique comment annuler une réservation et dans quelles conditions vous êtes remboursé. Elle reprend
            l’annexe 1 des <Link href="/cgv">conditions générales de vente</Link>, qui font foi.
          </p>
          <p>
            Votre paiement est conservé par Kwa-Ba : l’hôte n’est payé que 24 heures après votre arrivée, le propriétaire du véhicule
            après le début de la location. C’est ce qui nous permet de vous rembourser rapidement en cas d’annulation ou de problème.
          </p>
        </>
      }
      sections={[
        {
          id: "annuler",
          titre: "Annuler une réservation",
          contenu: (
            <ul>
              <li>Depuis <Link href="/profil/reservations">Mon profil → Mes réservations</Link>, bouton « Annuler » sur la réservation concernée.</li>
              <li>L’heure de l’annulation est celle enregistrée par Kwa-Ba, à l’heure de Lomé (GMT).</li>
              <li>Le montant remboursé est affiché avant que vous confirmiez l’annulation.</li>
            </ul>
          ),
        },
        {
          id: "reflexion",
          titre: "Délai de réflexion de 48 heures",
          contenu: (
            <p>
              Toute réservation de logement ou de mobilité annulée dans les <strong>48 heures</strong> suivant sa confirmation, et au moins{" "}
              <strong>7 jours</strong> avant l’arrivée ou la prise du véhicule, est remboursée intégralement, frais de service compris, quelle
              que soit la politique de l’annonce.
            </p>
          ),
        },
        {
          id: "logement",
          titre: "Logements : la politique choisie par l'hôte",
          contenu: (
            <>
              <p>Chaque hôte choisit l’une des trois politiques ci-dessous. Elle est affichée sur l’annonce et dans le récapitulatif avant le paiement.</p>
              <TableauHebergement />
              <ul>
                <li><strong>Séjours de 28 nuits ou plus :</strong> le premier mois n’est pas remboursable en cas d’annulation moins de 30 jours avant l’arrivée ; les mois suivants sont remboursés si vous prévenez au moins 30 jours à l’avance.</li>
                <li><strong>Non-présentation sans annulation :</strong> aucun remboursement.</li>
                <li><strong>Frais de ménage :</strong> remboursés si vous n’êtes pas arrivé.</li>
                <li><strong>Hôtels :</strong> la politique propre de l’hôtel s’applique si elle vous est plus favorable.</li>
              </ul>
            </>
          ),
        },
        {
          id: "mobilite",
          titre: "Transferts, voitures et chauffeurs",
          contenu: (
            <>
              <TableauMobilite />
              <p>En cas d’annulation tardive, la part du chauffeur lui est versée. Si votre vol est retardé, prévenez le chauffeur ; l’attente au-delà d’une heure peut être facturée en heures supplémentaires (1 000 F CFA l’heure).</p>
              <p>La caution d’une voiture sans chauffeur, payée en ligne, vous est toujours rendue en entier si vous annulez.</p>
            </>
          ),
        },
        {
          id: "prestataire",
          titre: "Annulation par l'hôte, le propriétaire ou Kwa-Ba",
          contenu: (
            <ul>
              <li>Si le prestataire annule, ou si Kwa-Ba annule une réservation (annonce non conforme, fraude, problème de sécurité), vous êtes <strong>remboursé intégralement</strong>, frais de service compris, et Kwa-Ba vous aide à trouver une solution équivalente.</li>
              <li>Si le logement ou le véhicule ne correspond pas à l’annonce, la <Link href="/cgv#garantie">Garantie Kwa-Ba</Link> s’applique : signalez-le dans les 24 heures suivant votre arrivée (avant le départ pour un véhicule), photos à l’appui.</li>
            </ul>
          ),
        },
        {
          id: "exceptionnelles",
          titre: "Circonstances exceptionnelles",
          contenu: (
            <>
              <p>
                Vous êtes remboursé intégralement, frais de service compris, si la prestation devient impossible ou interdite pour l’un des
                motifs suivants, survenu après la réservation et justifié : catastrophe naturelle ; épidémie déclarée avec des restrictions de
                déplacement ; fermeture des frontières ; interdiction officielle de voyager ; couvre-feu ou troubles graves dans la zone ;
                décès ou hospitalisation grave de vous-même ou d’un proche parent. Vous pouvez choisir un avoir à la place.
              </p>
              <p>Ne sont pas couverts : les retards ou annulations de vol ordinaires, les difficultés de visa connues à la réservation, les maladies sans hospitalisation, et les événements connus à la date de la réservation.</p>
            </>
          ),
        },
        {
          id: "delais",
          titre: "Délais et moyens de remboursement",
          contenu: (
            <ul>
              <li>Le remboursement est fait sur le moyen de paiement utilisé (Mobile Money, carte bancaire ou PayPal), dans un délai de <strong>7 jours ouvrés</strong>, auquel peut s’ajouter le délai de votre opérateur ou de votre banque.</li>
              <li>Si ce n’est pas possible, il est fait sur un compte Mobile Money à votre nom, avec votre accord.</li>
              <li>Un paiement PayPal est remboursé en euros, au prorata du montant remboursé.</li>
              <li>Une question sur un remboursement : <LienContact sujet="Remboursement" />.</li>
            </ul>
          ),
        },
      ]}
    />
  );
}
