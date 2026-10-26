import { Link } from "@/i18n/navigation";
import LienContact from "@/components/legal/LienContact";
import LegalPage, { VersionFrancaiseFaitFoi } from "@/components/legal/LegalPage";

/** Numbered paragraph of an article (“4.1. …”). */
function N({ n, children }: { n: string; children: React.ReactNode }) {
  return <p><strong>{n}.</strong> {children}</p>;
}

/** English version (the French version prevails). */
export default function ContenuEn() {
  return (
    <LegalPage
      titre="Terms of use"
      miseAJour="23 October 2026"
      intro={
        <>
          <VersionFrancaiseFaitFoi />
          <p>
            These terms set the rules for using the Kwa-Ba platform by all its users: visitors, customers and partners. They include the
            review charter (article 8). They are supplemented by the <Link href="/cgv">terms of sale</Link>, the{" "}
            <Link href="/confidentialite">privacy policy</Link>, the <Link href="/cookies">cookie policy</Link> and the{" "}
            <Link href="/mentions-legales">legal notice</Link>.
          </p>
        </>
      }
      sections={[
        {
          id: "objet",
          titre: "Purpose",
          contenu: (
            <>
              <N n="1.1">These terms of use (the “Terms of Use”) set the rules for accessing and using the kwa-ba.com website and the Kwa-Ba applications (the “Platform”), published by KWA-BA.</N>
              <N n="1.2">Anyone using the Platform accepts the Terms of Use. Creating an account requires accepting them expressly by ticking the box provided.</N>
              <N n="1.3">Booking a service is also governed by the <Link href="/cgv">terms of sale</Link>. Publication of an offer by a partner is governed by the common partner conditions, the Kwa-Ba Partners Network charter and the contract specific to its activity. In the event of conflict, the listing’s special conditions prevail, then the terms of sale, then the Terms of Use.</N>
            </>
          ),
        },
        {
          id: "definitions",
          titre: "Definitions",
          contenu: (
            <table>
              <thead><tr><th>Term</th><th>Meaning</th></tr></thead>
              <tbody>
                <tr><td>User</td><td>Anyone who views or uses the Platform, with or without an account</td></tr>
                <tr><td>Customer</td><td>A user who books or buys a service on the Platform</td></tr>
                <tr><td>Partner</td><td>Host, hotel, vehicle owner, driver, landlord, canvasser, referrer, field agent, excursion or event organiser offering services or working with KWA-BA</td></tr>
                <tr><td>Listing</td><td>Description of an offer published on the Platform by a partner and checked by KWA-BA</td></tr>
                <tr><td>Content</td><td>Text, photo, video, review or message published by a user</td></tr>
                <tr><td>Account</td><td>The user’s personal area, protected by their credentials</td></tr>
              </tbody>
            </table>
          ),
        },
        {
          id: "role",
          titre: "Role of KWA-BA",
          contenu: (
            <>
              <N n="3.1">KWA-BA is an <strong>intermediary</strong>. It connects customers and partners, checks listings, collects payments on behalf of partners through a licensed payment provider, and deducts its fees and commissions.</N>
              <N n="3.2">KWA-BA is not a hotelier, car rental company, carrier, travel agency, excursion or event organiser, or property manager. The partner alone performs its service and is liable for it, under the terms of sale.</N>
              <N n="3.3">The services offered on the Platform, and their opening date, are shown on the Platform. A service not yet open may be subject to a waiting list registration, without payment.</N>
            </>
          ),
        },
        {
          id: "compte",
          titre: "Access to the Platform and account",
          contenu: (
            <>
              <N n="4.1">Browsing listings is free. Booking, publishing a listing and posting a review require an account.</N>
              <N n="4.2">To open an account, the user must be an adult natural person (18) with legal capacity, or act for a legal entity they are authorised to represent. They provide accurate and up-to-date information: surname, first name, email address, phone number, country of residence.</N>
              <N n="4.3">A user may have only one account. They keep their credentials confidential and are responsible for their use. They notify KWA-BA without delay of any fraudulent use.</N>
              <N n="4.4">KWA-BA may request an identity document before a booking or publication, in particular for a partner, a rental without driver or a large amount. It may refuse to open an account in case of false declaration or safety risk.</N>
              <N n="4.5">The user may close their account at any time from their area or by message. Ongoing bookings remain governed by the terms of sale; data are kept according to the privacy policy.</N>
            </>
          ),
        },
        {
          id: "annonces",
          titre: "Partner listings",
          contenu: (
            <>
              <N n="5.1">Only a registered partner who has accepted the conditions concerning them may publish a listing. They guarantee that they are entitled to offer the service (ownership, mandate, operating licence) and hold the authorisations and insurance required by law.</N>
              <N n="5.2">Before publication, KWA-BA checks the offer: partner identity, documents, on-site visit by a field agent or partner of KWA-BA. It may refuse, suspend or remove an inaccurate, non-compliant or risky listing. The check concerns the listing’s compliance; it neither takes over nor guarantees the partner’s service.</N>
              <N n="5.3">The listing describes the offer accurately and completely: recent, non-misleading photos for which the partner holds the rights, equipment, rules, prices including all taxes in F CFA, chosen cancellation conditions, any security deposit within the limits of the terms of sale.</N>
              <N n="5.4">The following are forbidden in a listing: contact details allowing business outside the Platform (phone, email, link to another site), illegal or discriminatory offers, prices different from those charged for the same service outside the Platform.</N>
              <N n="5.5">Listings are ranked according to criteria shown on the Platform: relevance to the search, availability, average rating, seniority and cancellation rate of the partner, and, where applicable, paid promotion, always labelled as such.</N>
            </>
          ),
        },
        {
          id: "messagerie",
          titre: "Messaging and transactions outside the Platform",
          contenu: (
            <>
              <N n="6.1">Messaging is used to prepare and follow a booking. Messages must remain courteous and related to the service.</N>
              <N n="6.2">It is forbidden to offer or accept a payment or booking outside the Platform for a service discovered on the Platform. Such transactions deprive the customer of the Kwa-Ba Guarantee and of any recourse against KWA-BA.</N>
              <N n="6.3">Any user may report such an offer. A verified report is rewarded with 5,000 F CFA (terms of sale, art. 16.2).</N>
            </>
          ),
        },
        {
          id: "paiements",
          titre: "Payments",
          contenu: (
            <>
              <N n="7.1">All payments are made through the Platform, via the licensed payment provider named in the <Link href="/mentions-legales">legal notice</Link>. KWA-BA does not store full card data.</N>
              <N n="7.2">Prices, fees, payment times, payments to partners and refunds are set by the <Link href="/cgv">terms of sale</Link>.</N>
            </>
          ),
        },
        {
          id: "avis",
          titre: "Review charter",
          contenu: (
            <>
              <N n="8.1"><strong>Who may publish.</strong> Only a customer who actually received a service booked and paid on the Platform may publish a review of it, within <strong>14 days</strong> of its end. The partner may publish a rating of the customer within the same period.</N>
              <N n="8.2"><strong>What a review contains.</strong> A score from 1 to 5 and an optional comment. The review concerns a personal, lived experience. It is honest, precise and respectful.</N>
              <N n="8.3"><strong>What is forbidden:</strong></N>
              <ul>
                <li>insulting, defamatory, discriminatory, threatening or obscene remarks;</li>
                <li>personal data of third parties (full name, phone, address);</li>
                <li>reviews written by the partner, their relatives, or in exchange for payment or benefit;</li>
                <li>reviews unrelated to the service, or advertising;</li>
                <li>reviews intended to harm a competitor.</li>
              </ul>
              <N n="8.4"><strong>Moderation.</strong> KWA-BA checks each review before publication, within 72 hours, against the above rules only. It does not remove a review because it is negative. A rejected review is rejected for a reason given to its author, who may edit it.</N>
              <N n="8.5"><strong>Right of reply.</strong> The partner may reply publicly to a review once, within 14 days, under the same rules of courtesy.</N>
              <N n="8.6"><strong>Reporting.</strong> Any user may report a review they consider contrary to the charter. KWA-BA re-examines it and informs the reporter of its decision.</N>
              <N n="8.7"><strong>Display.</strong> Reviews are displayed from newest to oldest, with their date and the date of the service. A listing’s average rating is calculated on all published reviews. No review is bought. KWA-BA does not change any rating. It may remove a review only in the cases provided for in articles 8.8 and 8.9.</N>
              <N n="8.8"><strong>Retention.</strong> Reviews remain published as long as the listing exists, and for 3 years at most. The author may request deletion of their review at any time.</N>
              <N n="8.9"><strong>Fake reviews.</strong> Publishing a fake review leads to its removal and may lead to suspension of the account (article 11).</N>
            </>
          ),
        },
        {
          id: "contenus",
          titre: "User content",
          contenu: (
            <>
              <N n="9.1">The user remains the owner of the rights to their content. By publishing it, they grant KWA-BA, for the duration of publication and worldwide, a free, non-exclusive licence to reproduce it, adapt it to the Platform’s format and distribute it on the Platform and in KWA-BA communications relating to the listing concerned.</N>
              <N n="9.2">The user guarantees that they hold the rights to their content, in particular the consent of people recognisable in their photos, and that it infringes no third-party rights.</N>
              <N n="9.3">KWA-BA may remove any manifestly illegal content or content contrary to the Terms of Use as soon as it becomes aware of it.</N>
            </>
          ),
        },
        {
          id: "interdits",
          titre: "Prohibited behaviour",
          contenu: (
            <>
              <p>It is forbidden, in particular:</p>
              <ul>
                <li>to provide false information or impersonate a third party;</li>
                <li>to use the Platform for illegal, fraudulent purposes or purposes contrary to public order;</li>
                <li>to collect other users’ data, or use bots or scraping programs;</li>
                <li>to disrupt the Platform or try to bypass its security;</li>
                <li>to harass, threaten or discriminate against another user;</li>
                <li>to reproduce all or part of the Platform without KWA-BA’s written permission.</li>
              </ul>
            </>
          ),
        },
        {
          id: "suspension",
          titre: "Suspension and closure of an account",
          contenu: (
            <>
              <N n="11.1">KWA-BA may suspend or close an account in the event of a serious breach of the Terms of Use, the terms of sale or the partner conditions: fraud, fake reviews, payment outside the Platform, violence, illegal activity, repeated misleading listings.</N>
              <N n="11.2">Except in an emergency related to safety or fraud, the user is first informed in writing of the alleged facts and has <strong>7 days</strong> to explain, by writing to <LienContact sujet="Challenge of a decision" />. The decision is reasoned.</N>
              <N n="11.3">Suspension does not affect bookings already paid, except in case of fraud or safety risk: they are then cancelled and refunded under the terms of sale (art. 18.3).</N>
            </>
          ),
        },
        {
          id: "responsabilite",
          titre: "Liability",
          contenu: (
            <>
              <N n="12.1">KWA-BA uses reasonable means to ensure access to and security of the Platform, without guaranteeing permanent availability. It may interrupt it for maintenance, informing users where possible.</N>
              <N n="12.2">KWA-BA checks listings before publication, but the partner remains solely responsible for their accuracy and for its service. KWA-BA’s liability towards customers is set by the terms of sale (art. 19) and the Kwa-Ba Guarantee (art. 12 of the terms of sale). The Kwa-Ba Guarantee is a commercial commitment of KWA-BA to the customer. It does not make KWA-BA the performer of the service, which remains owed by the partner.</N>
              <N n="12.3">KWA-BA is not liable for third-party sites linked from the Platform, nor for outages of telecommunications networks or of the payment provider, subject to the continuity plan provided in the terms of sale (art. 11.5).</N>
              <N n="12.4">Neither party is liable for a failure due to force majeure.</N>
            </>
          ),
        },
        {
          id: "donnees",
          titre: "Personal data and cookies",
          contenu: (
            <>
              <N n="13.1">KWA-BA processes users’ data in accordance with law no. 2019-014 of 29 October 2019 on the protection of personal data and its <Link href="/confidentialite">privacy policy</Link>, available at any time on the Platform.</N>
              <N n="13.2">The Platform uses cookies and trackers necessary for its operation and, with the user’s consent, the third-party service cookies described in the <Link href="/cookies">cookie policy</Link>. The user may change their choices at any time via the “Manage cookies” link at the bottom of the page.</N>
              <N n="13.3">The user may object at any time, free of charge, to receiving commercial messages, through the link in each message or from their account (law no. 2017-07, art. 37).</N>
            </>
          ),
        },
        {
          id: "modification",
          titre: "Changes to the Terms of Use",
          contenu: (
            <>
              <N n="14.1">KWA-BA may amend the Terms of Use to reflect changes in the Platform, the law or its services.</N>
              <N n="14.2">Any significant change is announced at least <strong>30 days</strong> in advance to account holders, by message or on the Platform. A user who refuses it may close their account free of charge before it takes effect.</N>
            </>
          ),
        },
        {
          id: "preuve",
          titre: "Evidence",
          contenu: <p>Data recorded by the Platform are binding between the parties unless proven otherwise: acceptance of the Terms of Use, messages, bookings, reviews, time-stamped photos. In accordance with law no. 2017-07, electronic documents have the same evidential value as paper documents.</p>,
        },
        {
          id: "droit",
          titre: "Governing law and disputes",
          contenu: (
            <>
              <N n="16.1">These terms are governed by Togolese law and the OHADA uniform acts, without depriving the consumer of the mandatory provisions of the country where they reside.</N>
              <N n="16.2">Any complaint is sent to KWA-BA through the Platform or to <LienContact sujet="Complaint" />; KWA-BA acknowledges receipt within 72 hours. The parties seek an amicable solution for 30 days.</N>
              <N n="16.3">Failing that, the dispute falls within the jurisdiction of the competent courts of Lomé, in particular the Lomé commercial court for professionals.</N>
            </>
          ),
        },
        {
          id: "concierge",
          titre: "AI Concierge",
          contenu: (
            <ul>
              <li>The Concierge is an artificial intelligence assistant (Gemini, by Google). You are talking to a machine, not a person.</li>
              <li>Its answers may contain errors. Prices and availability of accommodation and mobility services come from KWA-BA and are binding at the time of booking; other information (restaurants, opening hours, procedures) should be checked.</li>
              <li>The Concierge does not book or pay anything for you. Do not share bank details, Mobile Money codes or sensitive data with it.</li>
              <li>Its use is limited in number of messages per hour and per day.</li>
            </ul>
          ),
        },
      ]}
    />
  );
}
