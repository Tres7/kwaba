import { Link } from "@/i18n/navigation";
import LegalPage, { VersionFrancaiseFaitFoi } from "@/components/legal/LegalPage";
import GererCookiesBouton from "@/components/legal/GererCookiesBouton";

/** English version (the French version prevails). */
export default function ContenuEn() {
  return (
    <LegalPage
      titre="Cookie policy"
      miseAJour="23 October 2026"
      intro={
        <>
          <p>
            A cookie is a small file stored on your device when you visit a website. This page lists <strong>all</strong> the
            cookies and storage items Kwa-Ba uses, what they are for and how long they last.
          </p>
          <p>
            <strong>Kwa-Ba uses no analytics, advertising or social media cookies.</strong>
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
          titre: "Third-party content (with your consent)",
          contenu: (
            <>
              <p>
                <strong>Google Maps</strong> on listing pages. It only loads with your consent (banner, cookie settings or the
                “Show map” button). Once shown, Google receives your IP address and may set its own cookies, governed by{" "}
                <a href="https://policies.google.com/privacy" target="_blank" rel="noopener noreferrer">Google&apos;s privacy policy</a>.
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
                bottom of every page. Refusing does not stop you using Kwa-Ba: only the interactive map is replaced by a placeholder.
              </p>
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
