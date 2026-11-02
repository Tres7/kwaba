import { Link } from "@/i18n/navigation";
import GererCookiesBouton from "@/components/legal/GererCookiesBouton";
import LegalPage, { VersionFrancaiseFaitFoi } from "@/components/legal/LegalPage";

/** English version (the French version prevails). */
export default function ContenuEn() {
  return (
    <LegalPage
      titre="Cookie policy"
      miseAJour="31 October 2026"
      intro={
        <>
          <p>
            A cookie is a small file stored on your device when you visit a website. This page lists <strong>all</strong> the
            cookies and storage items Kwa-Ba uses, what they are for and how long they last.
          </p>
          <p>
            <strong>Kwa-Ba uses no advertising or social media cookies.</strong> Audience measurement only runs with your
            consent.
          </p>
          <GererCookiesBouton className="mt-2 px-5 py-3 rounded-xl bg-dark text-white text-sm font-bold">Manage my cookie choices</GererCookiesBouton>
          <VersionFrancaiseFaitFoi />
        </>
      }
      sections={[
        {
          id: "necessaires",
          titre: "Strictly necessary cookies",
          contenu: (
            <>
              <p>
                Essential for the site to work (signing in, security). They do not require consent and cannot be turned off from
                the site. Scripts cannot read them (“HttpOnly” option).
              </p>
              <table>
                <thead><tr><th>Name</th><th>Purpose</th><th>Duration</th></tr></thead>
                <tbody>
                  <tr><td><code>authjs.session-token</code></td><td>Keeps you signed in to your account (encrypted session).</td><td>5 minutes after you leave the site, or until you log out</td></tr>
                  <tr><td><code>authjs.csrf-token</code></td><td>Protects sign-in forms against fraudulent requests.</td><td>Until the browser is closed</td></tr>
                  <tr><td><code>authjs.callback-url</code></td><td>Takes you back to the page you were on after signing in.</td><td>Until the browser is closed</td></tr>
                </tbody>
              </table>
              <p className="text-sm">In production, these names are prefixed with <code>__Secure-</code> or <code>__Host-</code> (cookies sent over HTTPS only).</p>
            </>
          ),
        },
        {
          id: "confort",
          titre: "Preference cookie",
          contenu: (
            <>
              <p>
                It remembers a choice you made yourself and is used for nothing else, so it does not require consent. The site
                reads it to show the right language (so it is not “HttpOnly”).
              </p>
              <table>
                <thead><tr><th>Name</th><th>Purpose</th><th>Duration</th></tr></thead>
                <tbody>
                  <tr><td><code>NEXT_LOCALE</code></td><td>Remembers the language you chose (French or English).</td><td>1 year</td></tr>
                </tbody>
              </table>
            </>
          ),
        },
        {
          id: "mesure",
          titre: "Audience measurement, with your consent",
          contenu: (
            <>
              <p>
                If you accept, Google Analytics tells us which pages are viewed and where visits come from, so we can improve the
                site. Google then receives your IP address and sets the cookies below. The addresses sent contain no booking,
                conversation or personal link identifier, and advertising features are turned off.
              </p>
              <p>Without your consent, these cookies are not set and Google receives nothing.</p>
              <table>
                <thead><tr><th>Name</th><th>Purpose</th><th>Duration</th></tr></thead>
                <tbody>
                  <tr><td><code>_ga</code></td><td>Gives your browser a random identifier to count visits.</td><td>13 months after your last visit</td></tr>
                  <tr><td><code>_ga_…</code></td><td>Keeps the state of your visit.</td><td>13 months after your last visit</td></tr>
                </tbody>
              </table>
            </>
          ),
        },
        {
          id: "stockage",
          titre: "Browser local storage",
          contenu: (
            <table>
              <thead><tr><th>Name</th><th>Purpose</th><th>Duration</th></tr></thead>
              <tbody>
                <tr><td><code>kwaba_consentement</code></td><td>Remembers your cookie choices (date and preferences).</td><td>6 months, after which you are asked again</td></tr>
                <tr><td><code>kwaba_devise</code></td><td>Remembers the currency chosen to display prices (CFA franc or euro).</td><td>Until deleted</td></tr>
                <tr><td><code>kwaba_bientot_fermee</code></td><td>Remembers when the “Places to stay are coming very soon” window was closed so it is not shown again right away.</td><td>7 days</td></tr>
                <tr><td><code>kwaba_bientot_inscrit</code></td><td>Stops showing the “Places to stay are coming very soon” window once you have signed up for the opening announcement.</td><td>Until deleted</td></tr>
              </tbody>
            </table>
          ),
        },
        {
          id: "session",
          titre: "Browser session storage",
          contenu: (
            <>
              <p>These items delete themselves when the tab is closed.</p>
              <table>
                <thead><tr><th>Name</th><th>Purpose</th><th>Duration</th></tr></thead>
                <tbody>
                  <tr><td><code>verify_email</code></td><td>Keeps the address entered at sign-up during code verification.</td><td>Deleted after verification or when the tab is closed</td></tr>
                  <tr><td><code>splash_shown</code></td><td>Avoids showing the animated welcome screen on every page.</td><td>Until the tab is closed</td></tr>
                  <tr><td><code>kwaba_transfert_brouillon</code></td><td>Keeps your transfer request while you sign in to pay.</td><td>Deleted when you return to the page or close the tab</td></tr>
                  <tr><td><code>kwaba_bientot_vue</code></td><td>Avoids showing the “Places to stay are coming very soon” window on every page.</td><td>Until the tab is closed</td></tr>
                </tbody>
              </table>
            </>
          ),
        },
        {
          id: "tiers",
          titre: "Third-party content",
          contenu: (
            <>
              <p>
                <strong>OpenFreeMap base map</strong> on search, listing pages and the host space. It receives your IP address to
                show the map and sets no cookies (see its{" "}
                <a href="https://openfreemap.org/privacy/" target="_blank" rel="noopener noreferrer">privacy policy</a>).
              </p>
              <p>
                <strong>Sign in with Google</strong> (when offered): Google is only contacted when you click “Continue with Google”.
                Google may then use its own cookies to identify you.
              </p>
            </>
          ),
        },
        {
          id: "choix",
          titre: "Changing or withdrawing your consent",
          contenu: (
            <>
              <p>
                You can change your mind at any time, as easily as you gave your consent: use the “Manage cookies” link at the
                bottom of every page. Withdrawing your consent stops audience measurement and removes its cookies. Refusing does
                not stop you using Kwa-Ba.
              </p>
              <p>As long as audience measurement is not switched on for the site, you are not asked to choose.</p>
              <p>
                You can also delete cookies in your browser settings. More information:{" "}
                <a href="https://www.cnil.fr/fr/cookies-et-autres-traceurs/comment-se-proteger/maitriser-votre-navigateur" target="_blank" rel="noopener noreferrer">CNIL guide (in French)</a>.
              </p>
              <p>For how we handle your personal data in general, see our <Link href="/confidentialite">privacy policy</Link>.</p>
            </>
          ),
        },
      ]}
    />
  );
}
