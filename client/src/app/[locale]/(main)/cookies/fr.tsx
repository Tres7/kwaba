import { Link } from "@/i18n/navigation";
import GererCookiesBouton from "@/components/legal/GererCookiesBouton";
import LegalPage from "@/components/legal/LegalPage";

/** French version. */
export default function ContenuFr() {
  return (
    <LegalPage
      titre="Politique de cookies"
      miseAJour="31 octobre 2026"
      intro={
        <>
          <p>
            Un cookie est un petit fichier déposé sur votre appareil lors de la visite d&apos;un site. Cette page liste
            <strong> tous</strong> les cookies et éléments de stockage utilisés par Kwa-Ba, leur rôle et leur durée.
          </p>
          <p>
            <strong>Kwa-Ba n&apos;utilise aucun cookie de publicité ni de réseau social.</strong> La mesure d&apos;audience ne
            fonctionne qu&apos;avec votre accord.
          </p>
          <GererCookiesBouton className="mt-2 px-5 py-3 rounded-xl bg-dark text-white text-sm font-bold">Gérer mes choix de cookies</GererCookiesBouton>
        </>
      }
      sections={[
        {
          id: "necessaires",
          titre: "Cookies strictement nécessaires",
          contenu: (
            <>
              <p>
                Indispensables au fonctionnement du site (connexion, sécurité). Ils sont exemptés de consentement et ne
                peuvent pas être désactivés depuis le site. Ils sont inaccessibles aux scripts (option « HttpOnly »).
              </p>
              <table>
                <thead><tr><th>Nom</th><th>Rôle</th><th>Durée</th></tr></thead>
                <tbody>
                  <tr><td><code>authjs.session-token</code></td><td>Maintient votre connexion à votre compte (session chiffrée).</td><td>5 minutes après avoir quitté le site, ou jusqu&apos;à la déconnexion</td></tr>
                  <tr><td><code>authjs.csrf-token</code></td><td>Protège les formulaires de connexion contre les requêtes frauduleuses.</td><td>Fermeture du navigateur</td></tr>
                  <tr><td><code>authjs.callback-url</code></td><td>Vous ramène à la page consultée après la connexion.</td><td>Fermeture du navigateur</td></tr>
                </tbody>
              </table>
              <p className="text-sm">En production, ces noms sont précédés de <code>__Secure-</code> ou <code>__Host-</code> (cookies transmis uniquement en HTTPS).</p>
            </>
          ),
        },
        {
          id: "confort",
          titre: "Cookie de confort",
          contenu: (
            <>
              <p>
                Il retient un choix que vous avez fait vous-même, sans servir à autre chose : il est exempté de consentement.
                Le site le lit pour afficher la bonne langue (il n&apos;est donc pas « HttpOnly »).
              </p>
              <table>
                <thead><tr><th>Nom</th><th>Rôle</th><th>Durée</th></tr></thead>
                <tbody>
                  <tr><td><code>NEXT_LOCALE</code></td><td>Mémorise la langue choisie (français ou anglais).</td><td>1 an</td></tr>
                </tbody>
              </table>
            </>
          ),
        },
        {
          id: "mesure",
          titre: "Mesure d'audience, avec votre accord",
          contenu: (
            <>
              <p>
                Si vous l&apos;acceptez, Google Analytics nous indique quelles pages sont consultées et d&apos;où viennent les
                visites, pour améliorer le site. Google reçoit alors votre adresse IP et dépose les cookies ci-dessous. Les
                adresses transmises ne contiennent aucun identifiant de réservation, de conversation ou de lien personnel, et les
                fonctions publicitaires sont désactivées.
              </p>
              <p>Sans votre accord, ces cookies ne sont pas déposés et Google ne reçoit rien.</p>
              <table>
                <thead><tr><th>Nom</th><th>Rôle</th><th>Durée</th></tr></thead>
                <tbody>
                  <tr><td><code>_ga</code></td><td>Attribue un identifiant aléatoire à votre navigateur pour compter les visites.</td><td>13 mois après la dernière visite</td></tr>
                  <tr><td><code>_ga_…</code></td><td>Retient l&apos;état de votre visite.</td><td>13 mois après la dernière visite</td></tr>
                </tbody>
              </table>
            </>
          ),
        },
        {
          id: "stockage",
          titre: "Stockage local du navigateur",
          contenu: (
            <table>
              <thead><tr><th>Nom</th><th>Rôle</th><th>Durée</th></tr></thead>
              <tbody>
                <tr><td><code>kwaba_consentement</code></td><td>Mémorise vos choix de cookies (date et préférences).</td><td>6 mois, puis le choix vous est redemandé</td></tr>
                <tr><td><code>kwaba_devise</code></td><td>Retient la devise choisie pour l&apos;affichage des prix (FCFA ou euro).</td><td>Jusqu&apos;à suppression</td></tr>
                <tr><td><code>kwaba_bientot_fermee</code></td><td>Retient la date de fermeture de la fenêtre « Les logements arrivent très bientôt » pour ne pas la réafficher aussitôt.</td><td>7 jours</td></tr>
                <tr><td><code>kwaba_bientot_inscrit</code></td><td>Évite de vous reproposer la fenêtre « Les logements arrivent très bientôt » une fois inscrit à l&apos;annonce d&apos;ouverture.</td><td>Jusqu&apos;à suppression</td></tr>
              </tbody>
            </table>
          ),
        },
        {
          id: "session",
          titre: "Stockage de session du navigateur",
          contenu: (
            <>
              <p>Ces éléments s&apos;effacent d&apos;eux-mêmes à la fermeture de l&apos;onglet.</p>
              <table>
                <thead><tr><th>Nom</th><th>Rôle</th><th>Durée</th></tr></thead>
                <tbody>
                  <tr><td><code>verify_email</code></td><td>Retient l&apos;adresse saisie à l&apos;inscription le temps de la vérification par code.</td><td>Effacé après la vérification ou à la fermeture de l&apos;onglet</td></tr>
                  <tr><td><code>splash_shown</code></td><td>Évite de réafficher l&apos;écran d&apos;accueil animé à chaque page.</td><td>Fermeture de l&apos;onglet</td></tr>
                  <tr><td><code>kwaba_transfert_brouillon</code></td><td>Garde votre demande de transfert le temps de vous connecter pour payer.</td><td>Effacé au retour sur la page ou à la fermeture de l&apos;onglet</td></tr>
                  <tr><td><code>kwaba_bientot_vue</code></td><td>Évite de réafficher la fenêtre « Les logements arrivent très bientôt » à chaque page.</td><td>Fermeture de l&apos;onglet</td></tr>
                </tbody>
              </table>
            </>
          ),
        },
        {
          id: "tiers",
          titre: "Contenus de services tiers",
          contenu: (
            <>
              <p>
                <strong>Fond de carte OpenFreeMap</strong> sur la recherche, la fiche des logements et l&apos;espace hôte. Il reçoit
                votre adresse IP pour afficher la carte et ne dépose aucun cookie (voir sa{" "}
                <a href="https://openfreemap.org/privacy/" target="_blank" rel="noopener noreferrer">politique de confidentialité</a>).
              </p>
              <p>
                <strong>Connexion avec Google</strong> (si elle est proposée) : le service de Google n&apos;est contacté que lorsque vous
                cliquez sur « Continuer avec Google ». Google peut alors utiliser ses propres cookies pour vous identifier.
              </p>
            </>
          ),
        },
        {
          id: "choix",
          titre: "Modifier ou retirer votre consentement",
          contenu: (
            <>
              <p>
                Vous pouvez changer d&apos;avis à tout moment, aussi simplement que vous avez donné votre accord : lien
                « Gérer les cookies » en bas de chaque page. Retirer votre accord arrête la mesure d&apos;audience et
                supprime ses cookies. Refuser n&apos;empêche pas d&apos;utiliser Kwa-Ba.
              </p>
              <p>Tant que la mesure d&apos;audience n&apos;est pas activée sur le site, aucun choix ne vous est demandé.</p>
              <p>
                Vous pouvez aussi supprimer les cookies depuis les réglages de votre navigateur. Plus d&apos;informations :{" "}
                <a href="https://www.cnil.fr/fr/cookies-et-autres-traceurs/comment-se-proteger/maitriser-votre-navigateur" target="_blank" rel="noopener noreferrer">guide de la CNIL</a>.
              </p>
              <p>Pour le traitement de vos données personnelles en général, consultez notre <Link href="/confidentialite">politique de confidentialité</Link>.</p>
            </>
          ),
        },
      ]}
    />
  );
}
