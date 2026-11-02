import { Link } from "@/i18n/navigation";
import LienContact from "@/components/legal/LienContact";
import LegalPage, { AC, VersionFrancaiseFaitFoi } from "@/components/legal/LegalPage";
import FormeSociete from "@/components/legal/FormeSociete";
import MentionSociete from "@/components/legal/MentionSociete";

/** English version (the French version prevails). */
export default function ContenuEn() {
  return (
    <LegalPage
      titre="Privacy policy"
      miseAJour="31 October 2026"
      intro={
        <>
          <p>
            This policy explains what personal data Kwa-Ba collects, why, how long it is kept and how to exercise your rights, in
            line with Togolese law no. 2019-014 of 29 October 2019 on the protection of personal data and law no. 2017-07 on
            electronic transactions.
          </p>
          <p>We only collect the data the service needs. We sell no data and use no advertising tools.</p>
          <VersionFrancaiseFaitFoi />
        </>
      }
      sections={[
        {
          id: "responsable",
          titre: "Data controller",
          contenu: (
            <ul>
              <li>Controller: <strong>KWA-BA</strong>, <FormeSociete /> with a share capital of 100,000 F CFA, Totsi Gblenkomé district, street 243, Lomé (Togo), RCCM <MentionSociete cle="rccm" libelle="RCCM" />.</li>
              <li>Declaration to the personal data protection authority (IPDCP): no. <MentionSociete cle="ipdcp" libelle="declaration number" />.</li>
              <li>Contact about your data: <LienContact sujet="Data protection" />.</li>
              <li>Data officer within KWA-BA: <AC>name or position</AC>.</li>
            </ul>
          ),
        },
        {
          id: "donnees",
          titre: "Data collected and purposes",
          contenu: (
            <table>
              <thead><tr><th>Data</th><th>Why</th><th>Legal basis</th></tr></thead>
              <tbody>
                <tr><td>First name, last name, email, password (stored encrypted, never readable), role (traveller or host)</td><td>Create and secure your account</td><td>Performance of the contract (terms of use)</td></tr>
                <tr><td>Phone (optional)</td><td>Make it easier to get in touch about a booking</td><td>Consent (optional field)</td></tr>
                <tr><td>Google ID and profile photo (only if you use “Continue with Google”)</td><td>Simplified sign-in</td><td>Performance of the contract</td></tr>
                <tr><td>Bookings: dates, number of guests, amount, chosen payment method, message to the host</td><td>Manage your stay and pass it on to the host</td><td>Performance of the contract</td></tr>
                <tr><td>Payments: amount, status, transaction ID at FedaPay or PayPal, Mobile Money operator and number charged</td><td>Collect payment for the stay, refund you on the same payment method, accounting</td><td>Performance of the contract; legal obligation (accounting)</td></tr>
                <tr><td>Airport transfers: airport, flight time and number, passengers, luggage, destination address, phone number, message to the driver</td><td>Arrange your airport pick-up</td><td>Performance of the contract</td></tr>
                <tr><td>Partner drivers: identity, phone, vehicle, number plate, Mobile Money account</td><td>Assign rides and pay drivers</td><td>Performance of the contract</td></tr>
                <tr><td>Car hire: vehicle, option, pick-up and return places and dates, delivery address, number of people, phone number, details of your needs; if you drive: driver&apos;s name, licence number and country</td><td>Arrange the rental with the partner rental company</td><td>Performance of the contract</td></tr>
                <tr><td>Partner rental companies: company name, contact, phone, Mobile Money account</td><td>Assign rentals and pay rental companies</td><td>Performance of the contract</td></tr>
                <tr><td>Hosts: country, operator, Mobile Money number and account holder name</td><td>Pay hosts for their stays</td><td>Performance of the contract</td></tr>
                <tr><td>Hosts: acceptance of the pre-registration and signature of the host agreement (date and time, IP address, browser, version and fingerprint of the accepted text, name and signature for the agreement)</td><td>Prove the host&apos;s agreement in case of dispute</td><td>Performance of the contract; legitimate interest (proof)</td></tr>
                <tr><td>Hosts: ID document (type and copy), report of the visit of the place by a Kwa-Ba agent (checks made, comment, photos taken on site)</td><td>Check the host&apos;s identity and that the place matches the listing before it goes live, to protect travellers. Only Kwa-Ba agents can see the copy, never travellers</td><td>Legitimate interest (fraud prevention)</td></tr>
                <tr><td>Messages exchanged with hosts or travellers</td><td>Messaging and email notifications</td><td>Performance of the contract</td></tr>
                <tr><td>Reviews and ratings (published with your first name and last initial)</td><td>Inform other travellers</td><td>Legitimate interest (reliable reviews)</td></tr>
                <tr><td>Group trips (Kwa-Ba Together): trip name, destination, dates, members, proposed places and votes, itinerary, practical information, bookings you choose to share</td><td>Plan a trip with others</td><td>Performance of the contract</td></tr>
                <tr><td>Kwa-Ba Give donations: chosen NGO and project, amount, fees, payment method, consent to share your identity with the NGO</td><td>Collect the donation, pay it to the NGO, send you the confirmation and payout updates</td><td>Performance of the contract</td></tr>
                <tr><td>Conversations with the AI Concierge: your messages and the replies, suggested offers</td><td>Help you plan your stay; monitor the cost of the service</td><td>Performance of the contract (requested service)</td></tr>
                <tr><td>Favourites</td><td>Find saved places again</td><td>Performance of the contract</td></tr>
                <tr><td>Audience measurement, only with your consent: pages viewed, IP address, random browser identifier, device type</td><td>Knowing which pages are useful and improving the site</td><td>Consent</td></tr>
                <tr><td>Hosts: listings, exact position of the place (travellers only see an approximate zone), photos (metadata and GPS location removed on upload), calendar</td><td>Publish and manage places</td><td>Performance of the contract</td></tr>
                <tr><td>Temporary verification codes, number of attempts</td><td>Verify your email, secure password resets, block abuse</td><td>Legitimate interest (security)</td></tr>
                <tr><td>Chosen language (French or English)</td><td>Show the site in your language</td><td>Performance of the contract</td></tr>
              </tbody>
            </table>
          ),
        },
        {
          id: "pas-collecte",
          titre: "What we do not collect",
          contenu: (
            <ul>
              <li>No card number or Mobile Money PIN: payment details are entered directly on FedaPay&apos;s or PayPal&apos;s secure pages.</li>
              <li>No audience measurement, advertising trackers or profiling.</li>
              <li>No sensitive data (health, opinions, religion, ethnic origin), except supporting evidence you choose to provide for a cancellation due to exceptional circumstances (<Link href="/cgv#annulation">terms of sale, art. 11.4</Link>), used only for that purpose.</li>
              <li>No travellers&apos; ID documents, unless Kwa-Ba asks for one for a rental without driver or in case of suspected fraud (<Link href="/cgv#compte">terms of sale, art. 4.3</Link>).</li>
              <li>We never sell your data.</li>
              <li>The adults / children split entered during a search is not saved: only the total number of guests is.</li>
            </ul>
          ),
        },
        {
          id: "destinataires",
          titre: "Recipients and processors",
          contenu: (
            <ul>
              <li>The <strong>host</strong> of the place you book receives your name, the booking details and your message.</li>
              <li>A <strong>Kwa-Ba Give partner NGO</strong> only receives your name and email if you agreed to this when donating; otherwise your donation is shown to it as anonymous. The total amount paid out each month is published, without donors&apos; names.</li>
              <li>The <strong>partner driver</strong> for a transfer receives your name, phone number, flight number, number of passengers and bags, destination address and your message.</li>
              <li>The <strong>partner rental company</strong> for a car hire receives your name, phone number, the vehicle, places and dates, number of people, your details and, if you drive, the driver&apos;s name and licence details.</li>
              <li><strong>Members of a group trip</strong> see your first name and last initial, your votes, your proposals and the bookings you share with them (place, dates, amount).</li>
              <li>Kwa-Ba <strong>administrators</strong>, for moderation and support (restricted and logged access).</li>
              <li>Website and data hosting: IONOS SE, Elgendorfer Straße 57, 56410 Montabaur (Germany).</li>
              <li>Email delivery (codes, notifications): <strong>Brevo</strong> (Sendinblue SAS, Paris, France), with data hosted in the European Union. Receives your email address and the content of the messages sent.</li>
              <li><strong>FedaPay</strong> (Benin): Mobile Money and card payments, payouts to hosts and refunds. Receives your name, email, the amount and, for hosts, the payout number.</li>
              <li>
                <strong>Google</strong> (United States), for two uses, each only if you use it:
                <ul>
                  <li>AI Concierge (Gemini API): receives the content of your messages to generate replies and keeps the conversation history for up to 55 days so it can be continued. Used on a paid plan: under its terms, Google then does not use this data to improve its products. Do not include sensitive data.</li>
                  <li>Google sign-in: when you choose “Continue with Google”.</li>
                </ul>
                Google may process data outside the European Union, under the EU–US Data Privacy Framework.
              </li>
              <li><strong>PayPal</strong> (Europe): only if you choose this payment method. Receives the amount and the booking reference.</li>
              <li>Base map: <strong>OpenFreeMap</strong> (Hyperknot Software Kft., Hungary), which may go through the Cloudflare network. Receives your IP address when a map is shown, and sets no cookies.</li>
              <li>Unsplash: some illustration photos are loaded from its servers, which then receive your IP address.</li>
            </ul>
          ),
        },
        {
          id: "transferts",
          titre: "Transfers outside Togo",
          contenu: (
            <p>
              Some data are hosted or accessed outside Togo: by the website host, by Brevo (European Union) for sending emails, by
              KWA-BA&apos;s partners based in France for customer service and management, by Google (United States) for the AI Concierge,
              and by the payment provider FedaPay, based in Benin. These transfers comply with the conditions of law no. 2019-014 and,
              where required, are authorised by the IPDCP. They are covered by confidentiality and security commitments.
            </p>
          ),
        },
        {
          id: "durees",
          titre: "Retention periods",
          contenu: (
            <ul>
              <li>Verification codes: 10 minutes. Cookie choices: 6 months. Language choice: 1 year. Visit statistics: 14 months at most.</li>
              <li>Inactive account: 3 years after the last activity, then deleted or anonymised.</li>
              <li>Bookings and contracts concluded online (acceptances, signed contracts): 5 years after their performance (<Link href="/cgv#preuve">terms of sale, art. 22.2</Link>).</li>
              <li>Payments, payouts, refunds, invoices, donations and payouts to NGOs: 10 years (accounting records).</li>
              <li>Partners&apos; supporting documents (vehicle papers, licence, criminal record, contracts): for the duration of the relationship, then 5 years. The copy of a host&apos;s ID document is deleted as soon as the agent has checked the identity (only the document type and the result of the check are kept).</li>
              <li>Report and photos of a visit: as long as the listing is published, then 3 years.</li>
              <li>AI Concierge conversations: until you delete them (button in the conversation), and at most 12 months after the last message.</li>
              <li>Messages: 3 years after the last message in the conversation.</li>
              <li>Reviews: as long as the listing exists, and 3 years at most.</li>
              <li>Marketing data (newsletter, waiting list): 3 years after the last contact.</li>
              <li>Connection and security logs: 12 months.</li>
            </ul>
          ),
        },
        {
          id: "droits",
          titre: "Your rights",
          contenu: (
            <>
              <p>
                Under law no. 2019-014, you have the right to be informed about the use of your data, to access it and obtain a copy, to
                have it rectified or completed, to have it erased (unless the law requires it to be kept), to object to its use on
                legitimate grounds and, without reason and free of charge, to direct marketing, and to withdraw your consent at any time,
                for the future.
              </p>
              <ul>
                <li>Change your details: <Link href="/profil/edit">My profile → My details</Link>.</li>
                <li>Close your account: from the same page, under “Close my account”.</li>
                <li>Get a copy of your data or have it permanently erased: write to <LienContact sujet="My personal data" />, giving your name and your account email. We reply within one month; we may ask you to prove your identity.</li>
              </ul>
              <p>
                You may also contact the Togolese <strong>personal data protection authority (IPDCP)</strong>, or the authority of your
                country of residence (for example the CNIL in France).
              </p>
            </>
          ),
        },
        {
          id: "securite",
          titre: "Security",
          contenu: (
            <ul>
              <li>Passwords are hashed, never stored in plain text.</li>
              <li>Your sign-in session is kept in a cookie scripts cannot read; the access token is renewed every hour.</li>
              <li>Limits on attempts at verification codes and on sending messages.</li>
              <li>Photos uploaded by hosts are stripped of their metadata (including GPS location).</li>
              <li>Encrypted connection (HTTPS), access limited to those who need it, regular backups; payments processed by a licensed provider.</li>
              <li>In the event of a data breach presenting a risk to you, we inform you and notify the IPDCP as provided by law.</li>
            </ul>
          ),
        },
        {
          id: "mineurs",
          titre: "Minors",
          contenu: <p>The Platform is reserved for adults. We do not knowingly collect data about minors, except their name and age when a parent declares them as travellers.</p>,
        },
        {
          id: "modification",
          titre: "Changes to this policy",
          contenu: <p>We may change this policy. Any significant change is announced on the Platform and by message to account holders at least 30 days before it takes effect.</p>,
        },
      ]}
    />
  );
}
