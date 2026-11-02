import { Link } from "@/i18n/navigation";
import LienContact from "@/components/legal/LienContact";
import LegalPage, { AC } from "@/components/legal/LegalPage";
import FormeSociete from "@/components/legal/FormeSociete";
import MentionSociete from "@/components/legal/MentionSociete";

/** French version. */
export default function ContenuFr() {
  return (
    <LegalPage
      titre="Politique de confidentialité"
      miseAJour="31 octobre 2026"
      intro={
        <>
          <p>
            Cette politique explique quelles données personnelles Kwa-Ba collecte, pourquoi, combien de temps elles sont
            conservées et comment exercer vos droits, conformément à la loi togolaise n° 2019-014 du 29 octobre 2019 relative à la
            protection des données à caractère personnel et à la loi n° 2017-07 relative aux transactions électroniques.
          </p>
          <p>Nous ne collectons que les données nécessaires au service. Nous ne vendons aucune donnée et n&apos;utilisons aucun outil publicitaire.</p>
        </>
      }
      sections={[
        {
          id: "responsable",
          titre: "Responsable du traitement",
          contenu: (
            <ul>
              <li>Responsable : <strong>KWA-BA</strong>, <FormeSociete /> au capital de 100 000 F CFA, quartier Totsi Gblenkomé, rue 243, Lomé (Togo), RCCM <MentionSociete cle="rccm" libelle="RCCM" />.</li>
              <li>Déclaration auprès de l&apos;Instance de protection des données à caractère personnel (IPDCP) : n° <MentionSociete cle="ipdcp" libelle="numéro de déclaration" />.</li>
              <li>Contact pour vos données : <LienContact sujet="Protection des données" />.</li>
              <li>Référent chargé des données au sein de KWA-BA : <AC>nom ou fonction</AC>.</li>
            </ul>
          ),
        },
        {
          id: "donnees",
          titre: "Données collectées et finalités",
          contenu: (
            <table>
              <thead><tr><th>Données</th><th>Pourquoi</th><th>Base légale</th></tr></thead>
              <tbody>
                <tr><td>Prénom, nom, email, mot de passe (stocké chiffré, jamais lisible), rôle (voyageur ou hôte)</td><td>Créer et sécuriser votre compte</td><td>Exécution du contrat (CGU)</td></tr>
                <tr><td>Téléphone (facultatif)</td><td>Faciliter le contact lié à une réservation</td><td>Consentement (champ facultatif)</td></tr>
                <tr><td>Identifiant et photo de profil Google (uniquement si vous utilisez « Continuer avec Google »)</td><td>Connexion simplifiée</td><td>Exécution du contrat</td></tr>
                <tr><td>Réservations : dates, nombre de voyageurs, montant, mode de paiement choisi, message à l&apos;hôte</td><td>Gérer votre séjour et le transmettre à l&apos;hôte</td><td>Exécution du contrat</td></tr>
                <tr><td>Paiements : montant, statut, identifiant de la transaction chez FedaPay ou PayPal, opérateur et numéro Mobile Money débité</td><td>Encaisser le séjour, vous rembourser sur le même moyen de paiement, comptabilité</td><td>Exécution du contrat ; obligation légale (comptabilité)</td></tr>
                <tr><td>Transferts aéroport : aéroport, heure et numéro de vol, passagers, bagages, adresse de destination, numéro de téléphone, message au chauffeur</td><td>Organiser la prise en charge à l&apos;aéroport</td><td>Exécution du contrat</td></tr>
                <tr><td>Chauffeurs partenaires : identité, téléphone, véhicule, immatriculation, compte Mobile Money</td><td>Attribuer les courses et payer les chauffeurs</td><td>Exécution du contrat</td></tr>
                <tr><td>Location de voiture : véhicule, formule, lieux et dates de remise et de retour, adresse de livraison, nombre de personnes, numéro de téléphone, précisions sur votre besoin ; si vous conduisez : nom du conducteur, numéro et pays du permis</td><td>Organiser la location avec le loueur partenaire</td><td>Exécution du contrat</td></tr>
                <tr><td>Loueurs partenaires : nom de l&apos;agence, contact, téléphone, compte Mobile Money</td><td>Attribuer les locations et payer les loueurs</td><td>Exécution du contrat</td></tr>
                <tr><td>Hôtes : pays, opérateur, numéro Mobile Money et nom du titulaire</td><td>Verser à l&apos;hôte le prix de ses séjours</td><td>Exécution du contrat</td></tr>
                <tr><td>Hôtes : acceptation de la pré-inscription et signature du contrat hôte (date et heure, adresse IP, navigateur, version et empreinte du texte accepté, nom et signature pour le contrat)</td><td>Prouver l&apos;accord de l&apos;hôte en cas de litige</td><td>Exécution du contrat ; intérêt légitime (preuve)</td></tr>
                <tr><td>Hôtes : pièce d&apos;identité (type et copie), compte rendu de la visite du logement par un agent Kwa-Ba (points contrôlés, commentaire, photos prises sur place)</td><td>Vérifier l&apos;identité de l&apos;hôte et la conformité du logement avant publication, pour protéger les voyageurs. La copie n&apos;est visible que des agents Kwa-Ba, jamais des voyageurs</td><td>Intérêt légitime (prévention de la fraude)</td></tr>
                <tr><td>Messages échangés avec les hôtes ou les voyageurs</td><td>Messagerie et notifications par email</td><td>Exécution du contrat</td></tr>
                <tr><td>Avis et notes (publiés avec votre prénom et l&apos;initiale de votre nom)</td><td>Informer les autres voyageurs</td><td>Intérêt légitime (fiabilité des avis)</td></tr>
                <tr><td>Voyages de groupe (Kwa-Ba Together) : nom du voyage, destination, dates, membres, logements proposés et votes, itinéraire, informations pratiques, réservations que vous choisissez de partager</td><td>Préparer un voyage à plusieurs</td><td>Exécution du contrat</td></tr>
                <tr><td>Dons Kwa-Ba Give : ONG et projet choisis, montant, frais, moyen de paiement, accord pour transmettre votre identité à l&apos;ONG</td><td>Encaisser le don, le reverser à l&apos;ONG, vous envoyer la confirmation et le suivi du reversement</td><td>Exécution du contrat</td></tr>
                <tr><td>Conversations avec le Concierge IA : vos messages et les réponses, offres proposées</td><td>Vous aider à organiser votre séjour ; suivi du coût du service</td><td>Exécution du contrat (service demandé)</td></tr>
                <tr><td>Favoris</td><td>Retrouver les logements sauvegardés</td><td>Exécution du contrat</td></tr>
                <tr><td>Mesure d&apos;audience, seulement avec votre accord : pages consultées, adresse IP, identifiant aléatoire du navigateur, type d&apos;appareil</td><td>Savoir quelles pages sont utiles et améliorer le site</td><td>Consentement</td></tr>
                <tr><td>Hôtes : annonces, position exacte du logement (les voyageurs ne voient qu&apos;une zone approximative), photos (métadonnées et position GPS supprimées à l&apos;envoi), calendrier</td><td>Publier et gérer les logements</td><td>Exécution du contrat</td></tr>
                <tr><td>Codes de vérification temporaires, nombre de tentatives</td><td>Vérifier votre email, sécuriser la réinitialisation du mot de passe, bloquer les abus</td><td>Intérêt légitime (sécurité)</td></tr>
                <tr><td>Langue choisie (français ou anglais)</td><td>Afficher le site dans votre langue</td><td>Exécution du contrat</td></tr>
              </tbody>
            </table>
          ),
        },
        {
          id: "pas-collecte",
          titre: "Ce que nous ne collectons pas",
          contenu: (
            <ul>
              <li>Aucun numéro de carte bancaire ni code Mobile Money : le paiement est saisi directement sur les pages sécurisées de FedaPay ou de PayPal.</li>
              <li>Aucune mesure d&apos;audience, aucun traceur publicitaire, aucun profilage.</li>
              <li>Aucune donnée sensible (santé, opinions, religion, origine ethnique), sauf un justificatif que vous choisissez de fournir pour une annulation pour circonstances exceptionnelles (<Link href="/cgv#annulation">CGV, art. 11.4</Link>), utilisé uniquement à cette fin.</li>
              <li>Aucune pièce d&apos;identité des voyageurs, sauf si Kwa-Ba la demande pour une location sans chauffeur ou en cas de soupçon de fraude (<Link href="/cgv#compte">CGV, art. 4.3</Link>).</li>
              <li>Nous ne vendons jamais vos données.</li>
              <li>La répartition adultes / enfants saisie lors d&apos;une recherche n&apos;est pas enregistrée : seul le nombre total de voyageurs l&apos;est.</li>
            </ul>
          ),
        },
        {
          id: "destinataires",
          titre: "Destinataires et sous-traitants",
          contenu: (
            <ul>
              <li>L&apos;<strong>hôte</strong> du logement que vous réservez reçoit votre nom, les détails de la réservation et votre message.</li>
              <li>Une <strong>ONG partenaire de Kwa-Ba Give</strong> ne reçoit votre nom et votre email que si vous l&apos;avez accepté au moment du don ; sinon, votre don lui est présenté comme anonyme. Le montant total reversé chaque mois est publié, sans le nom des donateurs.</li>
              <li>Le <strong>chauffeur partenaire</strong> d&apos;un transfert reçoit votre nom, votre numéro de téléphone, votre numéro de vol, le nombre de passagers et de bagages, l&apos;adresse de destination et votre message.</li>
              <li>Le <strong>loueur partenaire</strong> d&apos;une location de voiture reçoit votre nom, votre numéro de téléphone, le véhicule, les lieux et dates, le nombre de personnes, vos précisions et, si vous conduisez, le nom du conducteur et les références de son permis.</li>
              <li>Les <strong>membres d&apos;un voyage de groupe</strong> voient votre prénom et l&apos;initiale de votre nom, vos votes, vos propositions et les réservations que vous partagez avec eux (logement, dates, montant).</li>
              <li>Les <strong>administrateurs</strong> de Kwa-Ba, pour la modération et l&apos;assistance (accès restreint et tracé).</li>
              <li>Hébergement du site et des données : IONOS SE, Elgendorfer Straße 57, 56410 Montabaur (Allemagne).</li>
              <li>Envoi des emails (codes, notifications) : <strong>Brevo</strong> (Sendinblue SAS, Paris, France), données hébergées dans l&apos;Union européenne. Reçoit votre adresse email et le contenu des messages envoyés.</li>
              <li><strong>FedaPay</strong> (Bénin) : encaissement Mobile Money et carte, versements aux hôtes et remboursements. Reçoit votre nom, votre email, le montant et, pour les hôtes, le numéro de versement.</li>
              <li>
                <strong>Google</strong> (États-Unis), pour trois usages, chacun seulement si vous y recourez ou l&apos;acceptez :
                <ul>
                  <li>Concierge IA (API Gemini) : reçoit le contenu de vos messages pour générer les réponses et conserve l&apos;historique de la conversation jusqu&apos;à 55 jours pour pouvoir la poursuivre. Service utilisé en offre payante : selon ses conditions, Google n&apos;utilise alors pas ces données pour améliorer ses produits. N&apos;y indiquez pas de données sensibles.</li>
                  <li>Connexion avec Google : lorsque vous choisissez « Continuer avec Google ».</li>
                  <li>Mesure d&apos;audience (Google Analytics) : seulement avec votre accord. Reçoit les pages consultées, votre adresse IP et un identifiant aléatoire, sans fonction publicitaire. Statistiques conservées 14 mois au plus.</li>
                </ul>
                Google peut traiter des données hors de l&apos;Union européenne, dans le cadre du Data Privacy Framework UE–États-Unis.
              </li>
              <li><strong>PayPal</strong> (Europe) : uniquement si vous choisissez ce moyen de paiement. Reçoit le montant et la référence de la réservation.</li>
              <li>Fond de carte : <strong>OpenFreeMap</strong> (Hyperknot Software Kft., Hongrie), qui peut passer par le réseau Cloudflare. Reçoit votre adresse IP lorsqu&apos;une carte s&apos;affiche, sans déposer de cookie.</li>
              <li>Unsplash : certaines photos d&apos;illustration sont chargées depuis ses serveurs, qui reçoivent alors votre adresse IP.</li>
            </ul>
          ),
        },
        {
          id: "transferts",
          titre: "Transferts hors du Togo",
          contenu: (
            <p>
              Certaines données sont hébergées ou consultées hors du Togo : par l&apos;hébergeur du site, par Brevo (Union européenne) pour
              l&apos;envoi des emails, par les associés de KWA-BA établis en France pour le service client et la gestion, par Google (États-Unis)
              pour le Concierge IA et, avec votre accord, la mesure d&apos;audience, et par le prestataire de paiement FedaPay, établi au Bénin. Ces transferts se font dans le respect des
              conditions prévues par la loi n° 2019-014 et, le cas échéant, avec l&apos;autorisation de l&apos;IPDCP. Ils sont encadrés par des
              engagements de confidentialité et de sécurité.
            </p>
          ),
        },
        {
          id: "durees",
          titre: "Durées de conservation",
          contenu: (
            <ul>
              <li>Codes de vérification : 10 minutes. Choix de cookies : 6 mois. Choix de la langue : 1 an. Statistiques de visite : 14 mois au plus.</li>
              <li>Compte inactif : 3 ans après la dernière activité, puis suppression ou anonymisation.</li>
              <li>Réservations et contrats conclus en ligne (acceptations, contrats signés) : 5 ans après leur exécution (<Link href="/cgv#preuve">CGV, art. 22.2</Link>).</li>
              <li>Paiements, versements, remboursements, factures, dons et reversements aux ONG : 10 ans (pièces comptables).</li>
              <li>Justificatifs des partenaires (papiers du véhicule, permis, casier judiciaire, contrats) : pendant la relation, puis 5 ans. La copie de la pièce d&apos;identité d&apos;un hôte est supprimée dès que l&apos;agent a vérifié l&apos;identité (seuls le type de pièce et le résultat du contrôle sont conservés).</li>
              <li>Compte rendu et photos de la visite d&apos;un logement : tant que l&apos;annonce est publiée, puis 3 ans.</li>
              <li>Conversations avec le Concierge IA : jusqu&apos;à ce que vous les supprimiez (bouton dans la conversation), et au plus 12 mois après le dernier message.</li>
              <li>Messages : 3 ans après le dernier message de la conversation.</li>
              <li>Avis : tant que l&apos;annonce existe, et au plus 3 ans.</li>
              <li>Données de prospection (newsletter, liste d&apos;attente) : 3 ans après le dernier contact.</li>
              <li>Journaux de connexion et de sécurité : 12 mois.</li>
            </ul>
          ),
        },
        {
          id: "droits",
          titre: "Vos droits",
          contenu: (
            <>
              <p>
                Dans les conditions de la loi n° 2019-014, vous avez le droit d&apos;être informé de l&apos;utilisation de vos données, d&apos;y
                accéder et d&apos;en obtenir une copie, de les faire rectifier ou compléter, de les faire supprimer (sauf si leur conservation est
                exigée par la loi), de vous opposer à leur utilisation pour un motif légitime et, sans motif et sans frais, à la prospection
                commerciale, et de retirer votre consentement à tout moment, pour l&apos;avenir.
              </p>
              <ul>
                <li>Modifier vos informations : <Link href="/profil/edit">Mon profil → Mes informations</Link>.</li>
                <li>Fermer votre compte : depuis la même page, rubrique « Fermer mon compte ».</li>
                <li>Obtenir une copie de vos données ou leur effacement définitif : écrivez à <LienContact sujet="Mes données personnelles" />, en indiquant votre nom et l&apos;adresse de votre compte. Réponse sous un mois ; nous pouvons vous demander de justifier de votre identité.</li>
              </ul>
              <p>
                Vous pouvez aussi saisir l&apos;<strong>Instance de protection des données à caractère personnel (IPDCP)</strong> du Togo, ou
                l&apos;autorité de votre pays de résidence (par exemple la CNIL en France).
              </p>
            </>
          ),
        },
        {
          id: "securite",
          titre: "Sécurité",
          contenu: (
            <ul>
              <li>Mots de passe chiffrés (hachage), jamais stockés en clair.</li>
              <li>Session de connexion dans un cookie inaccessible aux scripts ; jeton d&apos;accès renouvelé toutes les heures.</li>
              <li>Limitation des tentatives sur les codes de vérification et sur l&apos;envoi de messages.</li>
              <li>Photos envoyées par les hôtes nettoyées de leurs métadonnées (dont la position GPS).</li>
              <li>Connexion chiffrée (HTTPS), accès limité aux personnes qui en ont besoin, sauvegardes régulières ; paiements traités par un prestataire agréé.</li>
              <li>En cas de violation de données présentant un risque pour vous, nous vous en informons et prévenons l&apos;IPDCP dans les conditions prévues par la loi.</li>
            </ul>
          ),
        },
        {
          id: "mineurs",
          titre: "Mineurs",
          contenu: <p>La Plateforme est réservée aux personnes majeures. Nous ne collectons pas sciemment de données sur des mineurs, sauf leur nom et leur âge lorsqu&apos;un parent les déclare comme voyageurs.</p>,
        },
        {
          id: "modification",
          titre: "Modification de la politique",
          contenu: <p>Nous pouvons modifier cette politique. Toute modification importante est annoncée sur la Plateforme et par message aux titulaires d&apos;un compte, au moins 30 jours avant son entrée en vigueur.</p>,
        },
      ]}
    />
  );
}
