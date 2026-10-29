import { Link } from "@/i18n/navigation";
import LienContact from "@/components/legal/LienContact";
import LegalPage from "@/components/legal/LegalPage";

/** Numbered paragraph of an article ("4.1. …"). */
function N({ n, children }: { n: string; children: React.ReactNode }) {
  return <p><strong>{n}.</strong> {children}</p>;
}

/** French version (authoritative). Terms of use and review charter, version 1 of 18 October 2026. */
export default function ContenuFr() {
  return (
    <LegalPage
      titre="Conditions générales d'utilisation"
      miseAJour="23 octobre 2026"
      intro={
        <p>
          Les présentes conditions fixent les règles d’utilisation de la plateforme Kwa-Ba par tous ses utilisateurs : visiteurs, clients et
          partenaires. Elles comprennent la charte des avis (article 8). Elles sont complétées par les{" "}
          <Link href="/cgv">conditions générales de vente</Link>, la <Link href="/confidentialite">politique de confidentialité</Link>, la{" "}
          <Link href="/cookies">politique de cookies</Link> et les <Link href="/mentions-legales">mentions légales</Link>.
        </p>
      }
      sections={[
        {
          id: "objet",
          titre: "Objet",
          contenu: (
            <>
              <N n="1.1">Les présentes conditions générales d’utilisation (les « CGU ») fixent les règles d’accès et d’utilisation du site kwa-ba.com et des applications Kwa-Ba (la « Plateforme »), éditées par KWA-BA.</N>
              <N n="1.2">Toute personne qui utilise la Plateforme accepte les CGU. La création d’un compte suppose de les accepter expressément, en cochant la case prévue.</N>
              <N n="1.3">La réservation d’un service est en outre régie par les <Link href="/cgv">conditions générales de vente</Link> (les « CGV »). La publication d’une offre par un partenaire est régie par les conditions communes aux partenaires, la charte du Réseau Kwa-Ba Partenaires et le contrat propre à son activité. En cas de contradiction, les conditions particulières de l’annonce priment, puis les CGV, puis les CGU.</N>
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
                <tr><td>Utilisateur</td><td>Toute personne qui consulte ou utilise la Plateforme, avec ou sans compte</td></tr>
                <tr><td>Client</td><td>Utilisateur qui réserve ou achète un service sur la Plateforme</td></tr>
                <tr><td>Partenaire</td><td>Hôte, hôtel, propriétaire de véhicule, chauffeur, bailleur, démarcheur, apporteur, relais, organisateur d’excursions ou d’événements qui propose ses services ou travaille avec KWA-BA</td></tr>
                <tr><td>Annonce</td><td>Description d’une offre publiée sur la Plateforme par un partenaire, vérifiée par KWA-BA</td></tr>
                <tr><td>Contenu</td><td>Texte, photo, vidéo, avis ou message publié par un utilisateur</td></tr>
                <tr><td>Compte</td><td>Espace personnel de l’utilisateur, protégé par ses identifiants</td></tr>
              </tbody>
            </table>
          ),
        },
        {
          id: "role",
          titre: "Rôle de KWA-BA",
          contenu: (
            <>
              <N n="3.1">KWA-BA est un <strong>intermédiaire</strong>. Elle met en relation les clients et les partenaires, vérifie les annonces, encaisse les paiements pour le compte des partenaires par un prestataire de paiement agréé, et prélève ses frais et commissions.</N>
              <N n="3.2">KWA-BA n’est ni hôtelier, ni loueur de véhicules, ni transporteur, ni agence de voyages, ni organisateur d’excursions ou d’événements, ni agent immobilier gestionnaire. Le partenaire exécute seul sa prestation et en répond, dans les conditions des CGV.</N>
              <N n="3.3">Les services proposés sur la Plateforme, et leur date d’ouverture, sont indiqués sur la Plateforme. Un service non encore ouvert peut faire l’objet d’une inscription sur une liste d’attente, sans paiement.</N>
            </>
          ),
        },
        {
          id: "compte",
          titre: "Accès à la Plateforme et compte",
          contenu: (
            <>
              <N n="4.1">La consultation des annonces est libre et gratuite. La réservation, la publication d’une annonce et le dépôt d’un avis supposent un compte.</N>
              <N n="4.2">Pour ouvrir un compte, l’utilisateur doit être une personne physique majeure (18 ans) et capable, ou agir pour une personne morale qu’il est autorisé à représenter. Il fournit des informations exactes et à jour : nom, prénom, adresse électronique, numéro de téléphone, pays de résidence.</N>
              <N n="4.3">Un utilisateur ne peut avoir qu’un seul compte. Il garde ses identifiants confidentiels et répond de leur utilisation. Il prévient KWA-BA sans délai en cas d’usage frauduleux.</N>
              <N n="4.4">KWA-BA peut demander une pièce d’identité avant une réservation ou une publication, notamment pour un partenaire, une location de véhicule sans chauffeur ou un montant élevé. Elle peut refuser l’ouverture d’un compte en cas de fausse déclaration ou de risque pour la sécurité.</N>
              <N n="4.5">L’utilisateur peut fermer son compte à tout moment depuis son espace ou par message. Les réservations en cours restent régies par les CGV ; les données sont conservées selon la politique de confidentialité.</N>
            </>
          ),
        },
        {
          id: "annonces",
          titre: "Annonces des partenaires",
          contenu: (
            <>
              <N n="5.1">Seul un partenaire inscrit, qui a accepté les conditions qui le concernent, peut publier une annonce. Il garantit qu’il a le droit d’offrir la prestation (propriété, mandat, autorisation d’exploiter) et qu’il détient les autorisations et assurances exigées par la loi.</N>
              <N n="5.2">Avant publication, KWA-BA vérifie l’offre : identité du partenaire, documents, visite sur place par un relais ou un associé. Elle peut refuser, suspendre ou retirer une annonce inexacte, non conforme ou présentant un risque. La vérification porte sur la conformité de l’annonce ; elle n’emporte ni reprise ni garantie de la prestation du partenaire.</N>
              <N n="5.3">L’annonce décrit l’offre de façon exacte et complète : photos récentes et non trompeuses, dont le partenaire détient les droits, équipements, règles, prix toutes taxes comprises en F CFA, conditions d’annulation choisies, dépôt de garantie éventuel dans les limites des CGV.</N>
              <N n="5.4">Sont interdits dans une annonce : les coordonnées permettant de traiter hors de la Plateforme (téléphone, courriel, lien vers un autre site), les offres illicites ou discriminatoires, les prix différents de ceux pratiqués pour la même prestation hors de la Plateforme.</N>
              <N n="5.5">Le classement des annonces dépend de critères affichés sur la Plateforme : pertinence par rapport à la recherche, disponibilité, note moyenne, ancienneté et taux d’annulation du partenaire, et, le cas échéant, mise en avant payante, toujours signalée comme telle.</N>
            </>
          ),
        },
        {
          id: "messagerie",
          titre: "Messagerie et transactions hors de la Plateforme",
          contenu: (
            <>
              <N n="6.1">La messagerie sert à préparer et à suivre une réservation. Les messages doivent rester courtois et en lien avec la prestation.</N>
              <N n="6.2">Il est interdit de proposer ou d’accepter un paiement ou une réservation hors de la Plateforme pour une prestation découverte sur la Plateforme. Ces opérations privent le client de la Garantie Kwa-Ba et de tout recours auprès de KWA-BA.</N>
              <N n="6.3">Tout utilisateur peut signaler une telle proposition. Un signalement vérifié est récompensé par 5 000 F CFA (CGV, art. 16.2).</N>
            </>
          ),
        },
        {
          id: "paiements",
          titre: "Paiements",
          contenu: (
            <>
              <N n="7.1">Tous les paiements se font par la Plateforme, par l’intermédiaire du prestataire de paiement agréé indiqué dans les <Link href="/mentions-legales">mentions légales</Link>. KWA-BA ne conserve pas les données complètes des cartes bancaires.</N>
              <N n="7.2">Les prix, les frais, les moments du paiement, les versements aux partenaires et les remboursements sont fixés par les <Link href="/cgv">CGV</Link>.</N>
            </>
          ),
        },
        {
          id: "avis",
          titre: "Charte des avis",
          contenu: (
            <>
              <N n="8.1"><strong>Qui peut publier.</strong> Seul un client qui a effectivement bénéficié d’une prestation réservée et payée sur la Plateforme peut publier un avis sur celle-ci, dans les <strong>14 jours</strong> suivant sa fin. Le partenaire peut publier une évaluation du client dans le même délai.</N>
              <N n="8.2"><strong>Ce que contient un avis.</strong> Une note de 1 à 5 et un commentaire facultatif. L’avis porte sur une expérience personnelle et vécue. Il est honnête, précis et respectueux.</N>
              <N n="8.3"><strong>Ce qui est interdit :</strong></N>
              <ul>
                <li>les propos injurieux, diffamatoires, discriminatoires, menaçants ou obscènes ;</li>
                <li>les données personnelles de tiers (nom complet, téléphone, adresse) ;</li>
                <li>les avis rédigés par le partenaire, par ses proches, ou contre rémunération ou avantage ;</li>
                <li>les avis sans lien avec la prestation, ou publicitaires ;</li>
                <li>les avis destinés à nuire à un concurrent.</li>
              </ul>
              <N n="8.4"><strong>Modération.</strong> KWA-BA vérifie chaque avis avant publication, dans un délai de 72 heures, au regard des seules règles ci-dessus. Elle ne supprime pas un avis parce qu’il est négatif. Un avis refusé l’est pour un motif communiqué à son auteur, qui peut le modifier.</N>
              <N n="8.5"><strong>Droit de réponse.</strong> Le partenaire peut répondre publiquement à un avis, une fois, dans les 14 jours, dans les mêmes conditions de courtoisie.</N>
              <N n="8.6"><strong>Signalement.</strong> Tout utilisateur peut signaler un avis qu’il estime contraire à la charte. KWA-BA réexamine l’avis et informe l’auteur du signalement de sa décision.</N>
              <N n="8.7"><strong>Affichage.</strong> Les avis sont affichés du plus récent au plus ancien, avec leur date et la date de la prestation. La note moyenne d’une annonce est calculée sur tous les avis publiés. Aucun avis n’est acheté. KWA-BA ne modifie aucune note. Elle peut retirer un avis dans les seuls cas prévus aux articles 8.8 et 8.9.</N>
              <N n="8.8"><strong>Conservation.</strong> Les avis restent publiés tant que l’annonce existe, et au plus 3 ans. L’auteur peut demander la suppression de son avis à tout moment.</N>
              <N n="8.9"><strong>Faux avis.</strong> La publication d’un faux avis entraîne son retrait et peut entraîner la suspension du compte (article 11).</N>
            </>
          ),
        },
        {
          id: "contenus",
          titre: "Contenus des utilisateurs",
          contenu: (
            <>
              <N n="9.1">L’utilisateur reste titulaire des droits sur ses contenus. En les publiant, il accorde à KWA-BA, pour la durée de leur publication et pour le monde entier, une licence gratuite et non exclusive de les reproduire, les adapter au format de la Plateforme et les diffuser sur la Plateforme et dans la communication de KWA-BA relative à l’annonce concernée.</N>
              <N n="9.2">L’utilisateur garantit qu’il détient les droits sur ses contenus, notamment l’accord des personnes reconnaissables sur ses photos, et qu’ils ne portent atteinte à aucun droit de tiers.</N>
              <N n="9.3">KWA-BA peut retirer tout contenu manifestement illicite ou contraire aux CGU, dès qu’elle en a connaissance.</N>
            </>
          ),
        },
        {
          id: "interdits",
          titre: "Comportements interdits",
          contenu: (
            <>
              <p>Il est interdit, notamment :</p>
              <ul>
                <li>de fournir des informations fausses ou d’usurper l’identité d’un tiers ;</li>
                <li>d’utiliser la Plateforme à des fins illicites, frauduleuses ou contraires à l’ordre public ;</li>
                <li>de collecter les données d’autres utilisateurs, ou d’utiliser des robots ou des programmes d’extraction ;</li>
                <li>de perturber le fonctionnement de la Plateforme ou de tenter d’en contourner la sécurité ;</li>
                <li>de harceler, menacer ou discriminer un autre utilisateur ;</li>
                <li>de reproduire tout ou partie de la Plateforme sans autorisation écrite de KWA-BA.</li>
              </ul>
            </>
          ),
        },
        {
          id: "suspension",
          titre: "Suspension et fermeture d'un compte",
          contenu: (
            <>
              <N n="11.1">KWA-BA peut suspendre ou fermer un compte en cas de manquement grave aux CGU, aux CGV ou aux conditions des partenaires : fraude, faux avis, paiement hors de la Plateforme, violence, activité illicite, annonces trompeuses répétées.</N>
              <N n="11.2">Sauf urgence liée à la sécurité ou à une fraude, l’utilisateur est d’abord informé par écrit des faits reprochés et dispose de <strong>7 jours</strong> pour s’expliquer, en écrivant à <LienContact sujet="Contestation d'une décision" />. La décision est motivée.</N>
              <N n="11.3">La suspension ne remet pas en cause les réservations déjà payées, sauf fraude ou risque pour la sécurité : elles sont alors annulées et remboursées selon les CGV (art. 18.3).</N>
            </>
          ),
        },
        {
          id: "responsabilite",
          titre: "Responsabilité",
          contenu: (
            <>
              <N n="12.1">KWA-BA met en œuvre des moyens raisonnables pour assurer l’accès et la sécurité de la Plateforme, sans garantir une disponibilité permanente. Elle peut l’interrompre pour maintenance, en prévenant les utilisateurs lorsque c’est possible.</N>
              <N n="12.2">KWA-BA vérifie les annonces avant publication, mais le partenaire reste seul responsable de leur exactitude et de sa prestation. La responsabilité de KWA-BA envers les clients est fixée par les CGV (art. 19) et la Garantie Kwa-Ba (art. 12 des CGV). La Garantie Kwa-Ba est un engagement commercial de KWA-BA envers le client. Elle ne fait pas de KWA-BA l’exécutant de la prestation, qui reste due par le partenaire.</N>
              <N n="12.3">KWA-BA n’est pas responsable des sites tiers vers lesquels la Plateforme renvoie, ni des pannes des réseaux de télécommunication ou du prestataire de paiement, sous réserve du plan de continuité prévu par les CGV (art. 11.5).</N>
              <N n="12.4">Aucune partie n’est responsable d’un manquement dû à la force majeure.</N>
            </>
          ),
        },
        {
          id: "donnees",
          titre: "Données personnelles et cookies",
          contenu: (
            <>
              <N n="13.1">KWA-BA traite les données des utilisateurs conformément à la loi n° 2019-014 du 29 octobre 2019 relative à la protection des données à caractère personnel et à sa <Link href="/confidentialite">politique de confidentialité</Link>, accessible à tout moment sur la Plateforme.</N>
              <N n="13.2">La Plateforme utilise des cookies et traceurs nécessaires à son fonctionnement et, avec l’accord de l’utilisateur, les cookies des services tiers décrits dans la <Link href="/cookies">politique de cookies</Link>. L’utilisateur peut à tout moment modifier ses choix depuis le lien « Gérer les cookies » en bas de page.</N>
              <N n="13.3">L’utilisateur peut s’opposer à tout moment, sans frais, à recevoir des messages commerciaux, par le lien prévu dans chaque message ou depuis son compte (loi n° 2017-07, art. 37).</N>
            </>
          ),
        },
        {
          id: "modification",
          titre: "Modification des CGU",
          contenu: (
            <>
              <N n="14.1">KWA-BA peut modifier les CGU pour tenir compte de l’évolution de la Plateforme, de la loi ou de ses services.</N>
              <N n="14.2">Toute modification importante est annoncée au moins <strong>30 jours</strong> à l’avance aux utilisateurs titulaires d’un compte, par message ou sur la Plateforme. L’utilisateur qui la refuse peut fermer son compte sans frais avant son entrée en vigueur.</N>
            </>
          ),
        },
        {
          id: "preuve",
          titre: "Preuve",
          contenu: <p>Les données enregistrées par la Plateforme font foi entre les parties, sauf preuve contraire : acceptation des CGU, messages, réservations, avis, photos horodatées. Conformément à la loi n° 2017-07, l’écrit électronique a la même force probante que l’écrit papier.</p>,
        },
        {
          id: "droit",
          titre: "Droit applicable et litiges",
          contenu: (
            <>
              <N n="16.1">Les présentes conditions sont soumises au droit togolais et aux actes uniformes de l’OHADA, sans priver le consommateur des dispositions impératives du pays où il réside.</N>
              <N n="16.2">Toute réclamation est adressée à KWA-BA par la Plateforme ou à <LienContact sujet="Réclamation" /> ; KWA-BA en accuse réception sous 72 heures. Les parties recherchent une solution amiable pendant 30 jours.</N>
              <N n="16.3">À défaut, le litige relève des juridictions compétentes de Lomé, notamment du tribunal de commerce de Lomé pour les professionnels.</N>
            </>
          ),
        },
        {
          id: "concierge",
          titre: "Concierge IA",
          contenu: (
            <ul>
              <li>Le Concierge est un assistant fondé sur l’intelligence artificielle (Gemini, de Google). Vous dialoguez avec une machine, pas avec une personne.</li>
              <li>Ses réponses peuvent contenir des erreurs. Les prix et disponibilités des logements et des services de mobilité proviennent de KWA-BA et font foi au moment de la réservation ; les autres informations (restaurants, horaires, démarches) sont à vérifier.</li>
              <li>Le Concierge ne réserve et ne paie rien à votre place. N’y communiquez ni coordonnées bancaires, ni code Mobile Money, ni données sensibles.</li>
              <li>Son usage est limité en nombre de messages par heure et par jour.</li>
            </ul>
          ),
        },
      ]}
    />
  );
}
