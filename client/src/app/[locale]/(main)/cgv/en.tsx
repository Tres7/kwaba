import { Link } from "@/i18n/navigation";
import LienContact from "@/components/legal/LienContact";
import MentionSociete from "@/components/legal/MentionSociete";
import LegalPage, { AC, VersionFrancaiseFaitFoi } from "@/components/legal/LegalPage";

/** Numbered paragraph of an article (“6.1. …”). */
function N({ n, children }: { n: string; children: React.ReactNode }) {
  return <p><strong>{n}.</strong> {children}</p>;
}

/** English version (the French version prevails). */
export default function ContenuEn() {
  return (
    <LegalPage
      titre="Terms of sale"
      miseAJour="23 October 2026"
      intro={
        <>
          <VersionFrancaiseFaitFoi />
          <p>
            The kwa-ba.com website and its applications (the “Platform”) are operated by <strong>KWA-BA SARL</strong>, a limited liability
            company (SARL) with a share capital of 100,000 F CFA, whose registered office is in the Totsi Gblenkomé district, street 243,
            Lomé (Togo), registered with the Lomé RCCM under number <MentionSociete cle="rccm" libelle="RCCM" />, tax number (NIF) <MentionSociete cle="nif" libelle="NIF" />, registered as an
            e-commerce provider under number <MentionSociete cle="commerce_electronique" libelle="registration number" />, represented by its co-managers (cogérants), Mr MENDE Fadel and Mr KPOGLO Dzidoula Godwin Trésor.
          </p>
          <ul className="list-disc pl-5 space-y-1">
            <li>Contact: <LienContact sujet="Terms of sale" />; postal address: Totsi Gblenkomé district, street 243, Lomé, Togo.</li>
            <li>Co-managers (cogérants): Mr MENDE Fadel and Mr KPOGLO Dzidoula Godwin Trésor — Publication director: Mr MENDE Fadel.</li>
          </ul>
          <p>
            These terms of sale (the “Terms of Sale”) supplement the <Link href="/cgu">terms of use</Link> and the{" "}
            <Link href="/confidentialite">privacy policy</Link> of the Platform.
          </p>
        </>
      }
      sections={[
        {
          id: "objet",
          titre: "Purpose and scope",
          contenu: (
            <>
              <N n="1.1">The Terms of Sale apply to any booking or order placed on the Platform by a customer. They cover the following services:</N>
              <ul>
                <li>short-term accommodation (hotels, furnished flats and houses);</li>
                <li>mobility: airport transfers, car with driver, car without driver, driver for the customer’s own vehicle.</li>
              </ul>
              <N n="1.2">Services opened later (long-term rental, Secure Rent, Kwa-Ba Direct Link, Kwa-Ba Pro, excursions, corporate framework agreements, Kwa-Ba Events ticketing) are governed by special conditions supplementing the Terms of Sale, published when they open.</N>
              <N n="1.3">In the event of conflict, the order of priority is: 1) the special conditions of the listing or service, displayed before booking; 2) the Terms of Sale; 3) the terms of use. A special condition of a listing may never reduce the rights granted to the customer by the Terms of Sale or by law; any such condition is deemed unwritten.</N>
              <N n="1.4">The Terms of Sale are written in French, which prevails in the event of translation.</N>
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
                <tr><td>Customer</td><td>Any person who books or orders a service: traveller, company</td></tr>
                <tr><td>Consumer</td><td>A customer who is a natural person acting for purposes outside their professional activity</td></tr>
                <tr><td>Professional</td><td>A customer acting for the needs of their activity (company, NGO, administration)</td></tr>
                <tr><td>Provider</td><td>The party providing the booked service: host, hotel, vehicle owner, driver</td></tr>
                <tr><td>Partner</td><td>Member of the Kwa-Ba Partners Network: canvasser, referrer, field agent, host, owner, driver</td></tr>
                <tr><td>Listing</td><td>The page describing the service, its price, rules, cancellation policy and, where applicable, its security deposit</td></tr>
                <tr><td>Price</td><td>The price set by the provider (nights, vehicle)</td></tr>
                <tr><td>Service fee</td><td>KWA-BA’s remuneration paid by the customer for its booking service</td></tr>
                <tr><td>Total price</td><td>The total amount displayed before payment: price, service fee, driver price, any taxes</td></tr>
                <tr><td>Security deposit</td><td>The sum given as security and returned at the end of the service (often called “caution”)</td></tr>
                <tr><td>Kwa-Ba Guarantee</td><td>KWA-BA’s commitments described in article 12</td></tr>
              </tbody>
            </table>
          ),
        },
        {
          id: "role",
          titre: "Role of KWA-BA",
          contenu: (
            <>
              <N n="3.1">KWA-BA acts as a <strong>commercial intermediary</strong>. It connects the customer and the provider, presents listings, organises bookings and, depending on the service, collects payment on behalf of the provider.</N>
              <N n="3.2">The accommodation, vehicle rental or transport contract is concluded <strong>directly between the customer and the provider</strong>. The provider is responsible for its service, its conformity with the listing and compliance with the rules applying to its activity: authorisations, insurance, tax returns, guest register.</N>
              <N n="3.3">KWA-BA provides in its own name: the booking service and assistance (service fee); KWA-BA’s share of the driver price; the Kwa-Ba Guarantee. It is liable for these services under article 19.</N>
              <N n="3.4">KWA-BA checks each listing before publication: visit of the accommodation, check of the vehicle papers (registration, roadworthiness test, insurance) and of the driver (licence, criminal record or certificate). This reduces risks but cannot guarantee the absence of any defect.</N>
              <N n="3.5">KWA-BA is not a hotelier, car rental company, carrier, property manager, event organiser or insurer.</N>
            </>
          ),
        },
        {
          id: "compte",
          titre: "Access to the service and account",
          contenu: (
            <>
              <N n="4.1">To book, the customer must be <strong>of age</strong>, legally capable of contracting, and hold an accurate and up-to-date personal account. They are responsible for keeping their credentials confidential.</N>
              <N n="4.2">A minor may stay in accommodation booked through the Platform only if accompanied by a parent or a responsible adult holding an authorisation. Otherwise the provider refuses access; the booking is then cancelled without refund and the facts may be reported to the authorities.</N>
              <N n="4.3">KWA-BA may request an identity document or other supporting documents before a booking, in particular for a vehicle rental without driver. A booking for which the documents are not provided may be cancelled with a full refund.</N>
              <N n="4.4">KWA-BA may cancel a booking, with a full refund, in the event of serious suspicion of fraud, identity theft, disputed payment or safety risk. It informs the customer.</N>
            </>
          ),
        },
        {
          id: "etapes",
          titre: "Booking steps",
          contenu: (
            <>
              <N n="5.1">Before paying, the customer sees a full summary: the booked service; dates and times; number of people; the itemised total price in F CFA; the cancellation policy; whether a right of withdrawal exists and how; any security deposit; the listing rules. They may correct their choices or abandon at any time.</N>
              <N n="5.2">The customer expressly accepts the Terms of Sale, the listing rules and the cancellation policy by ticking a box before paying. These documents can be viewed, downloaded and printed.</N>
              <N n="5.3">The booking is firm once payment is confirmed. KWA-BA sends a confirmation by email immediately after payment is confirmed, and within five days at the latest, containing the summary and the link to the Terms of Sale. An electronic receipt is issued for each payment.</N>
              <N n="5.4">Exchanges with the provider go through the Platform’s messaging, before and after payment. For a mobility mission, the driver’s name and number are given to the customer after assignment, at the latest 24 hours before the mission.</N>
              <N n="5.5"><strong>Booking request:</strong> where the listing provides for it, the provider has 24 hours to accept. Without an answer, the request is cancelled and any amount charged is fully refunded.</N>
            </>
          ),
        },
        {
          id: "prix",
          titre: "Prices and fees",
          contenu: (
            <>
              <N n="6.1">Prices are expressed in <strong>CFA francs, all taxes included</strong>. The total price displayed before payment is what the customer pays. <AC>KWA-BA VAT status</AC></N>
              <N n="6.2">The price is fixed at booking. It cannot be increased afterwards, except at the customer’s request (extension, additional person, option).</N>
              <N n="6.3"><strong>Obvious pricing error:</strong> if a displayed price is grossly wrong (for example 1,000 F CFA per night instead of 100,000), KWA-BA or the provider may cancel the booking with a full refund. No surcharge may be claimed from the customer.</N>
              <p className="font-semibold text-dark">6.4. Short-term accommodation</p>
              <table>
                <thead><tr><th>Item</th><th>Amount</th></tr></thead>
                <tbody>
                  <tr><td>Price of nights, any cleaning fee</td><td>Set by the host or hotel, displayed before booking</td></tr>
                  <tr><td>Customer service fee</td><td><strong>6%</strong> of the price of nights</td></tr>
                  <tr><td>Stay + Driver Pack (accommodation booked with a car with driver)</td><td>3% on the accommodation</td></tr>
                  <tr><td>Customer under a corporate framework agreement</td><td>4%</td></tr>
                  <tr><td>Loyal customer (new stay with the same host through the Platform)</td><td>3%</td></tr>
                  <tr><td>Tourist or local tax, if applicable</td><td>Shown on the listing and included in the total price</td></tr>
                </tbody>
              </table>
              <p>Reductions are not cumulative: the lowest rate applies.</p>
              <p className="font-semibold text-dark">6.5. Mobility</p>
              <table>
                <thead><tr><th>Item</th><th>Amount</th></tr></thead>
                <tbody>
                  <tr><td>Vehicle price (per day)</td><td>Set by the owner; <strong>no service fee</strong> for the customer</td></tr>
                  <tr><td>Airport transfer</td><td>Flat price per trip displayed by the Platform according to the airport and vehicle category, <strong>driver included</strong></td></tr>
                  <tr><td>Driver (car with driver, driver only)</td><td><strong>7,000 F CFA per day</strong> of up to 10 hours</td></tr>
                  <tr><td>Driver overtime hour</td><td>1,000 F CFA</td></tr>
                  <tr><td>Driver travel allowance</td><td>1,500 F CFA per day in the country outside Lomé; 2,000 F CFA per day outside the country</td></tr>
                  <tr><td>Fuel, tolls, parking</td><td>Paid by the customer, unless otherwise stated on the listing</td></tr>
                  <tr><td>Driver’s accommodation and meals for an overnight stay outside Lomé</td><td>As stated at booking</td></tr>
                  <tr><td>Mileage</td><td>Unlimited, unless a limit and an extra-kilometre price are shown on the listing</td></tr>
                  <tr><td>Security deposit (without driver only)</td><td>Article 14</td></tr>
                </tbody>
              </table>
            </>
          ),
        },
        {
          id: "paiement",
          titre: "Payment",
          contenu: (
            <>
              <N n="7.1">Payments are processed by <strong>FedaPay</strong>, a payment institution licensed by the BCEAO: Mobile Money (Moov Money, Mixx by Yas and other operators offered) and bank card (Visa, Mastercard). PayPal may also be offered when shown at payment. KWA-BA may use another licensed payment provider, in particular if FedaPay is unavailable. KWA-BA does not store full card data.</N>
              <N n="7.2">Depending on the service, the price is either collected by KWA-BA on behalf of the provider under the mandate given by the provider (payment to KWA-BA then counts as payment to the provider), or paid to the provider through the Platform. The applicable mode is shown at payment.</N>
              <N n="7.3">The price is always paid in F CFA. For a card issued outside the franc zone, the conversion is made by the customer’s bank at its rate. If PayPal is offered, the euro amount is shown before validation (fixed parity €1 = 655.957 F CFA). Any fees charged by the customer’s bank remain payable by the customer.</N>
              <N n="7.4">Payment provider fees are borne by KWA-BA, unless otherwise stated before payment.</N>
              <N n="7.5"><strong>Payment outside the Platform is forbidden.</strong> No payment may be made to the provider, driver or a canvasser in cash or by any other means for a service booked through the Platform. The only exception is an accommodation security deposit handed to the host against a receipt (article 13.5). A direct payment outside this case is not covered by the Kwa-Ba Guarantee.</N>
              <N n="7.6"><strong>Payment disputes:</strong> a customer who disputes with their bank or operator a payment for a service actually provided may have their account suspended and the sums due recovered. They are invited to contact KWA-BA first (article 21).</N>
            </>
          ),
        },
        {
          id: "versement",
          titre: "Payment to the provider",
          contenu: (
            <>
              <N n="8.1">Accommodation: the price is held until <strong>24 hours after the customer’s arrival</strong>, then paid to the host.</N>
              <N n="8.2">Mobility: the price is paid to the provider after the mission or rental has started; for a rental with a security deposit, after the damage reporting period (article 14.3).</N>
              <N n="8.3">These periods allow the customer to report a problem before the provider is paid.</N>
            </>
          ),
        },
        {
          id: "modification",
          titre: "Changes and extensions",
          contenu: (
            <>
              <N n="9.1">Any change (dates, number of people, duration) is requested through the Platform. It is only effective once the provider agrees and any difference is paid.</N>
              <N n="9.2">An extension of a stay or rental must be booked and paid through the Platform before the end of the current service.</N>
              <N n="9.3">Early departure or early return of the vehicle gives no right to a refund, unless the provider agrees or the Kwa-Ba Guarantee applies.</N>
            </>
          ),
        },
        {
          id: "retractation",
          titre: "Consumer right of withdrawal",
          contenu: (
            <>
              <N n="10.1">In accordance with law no. 2017-07 on electronic transactions (art. 44), the consumer may withdraw without giving reasons within <strong>ten working days</strong> of the conclusion of the contract. They give notice from their booking area or by email. The sums paid are refunded within 10 days of this notice (art. 46). This withdrawal period is not the same as the refund period after a cancellation, which is seven business days (article 11.5).</N>
              <N n="10.2">This right can no longer be exercised once performance of the service has begun with the consumer’s agreement before the end of this period (art. 47). By confirming a booking for specific dates, the consumer expressly requests that the booking service be performed immediately: the dates are blocked with the provider, who turns away other customers for those dates. The consumer acknowledges that they can then no longer exercise their right of withdrawal on those dates, and that the cancellation policy in annex 1 applies.</N>
              <N n="10.3"><strong>Free cooling-off period:</strong> even where the right of withdrawal does not apply, any short-term accommodation or mobility booking cancelled within <strong>48 hours</strong> of its confirmation, and at least <strong>7 days</strong> before arrival or vehicle pick-up, is fully refunded, service fee included.</N>
              <N n="10.4">Professional customers do not benefit from the right of withdrawal (art. 43 of the same law).</N>
            </>
          ),
        },
        {
          id: "annulation",
          titre: "Cancellation and refund",
          contenu: (
            <>
              <N n="11.1">The cancellation rules of each service are set out in <a href="#annexe-1">annex 1</a> and on the <Link href="/remboursement">Cancellation and refund</Link> page. The applicable rule is shown on the listing and in the summary before payment.</N>
              <N n="11.2">The customer cancels from their booking area. The time of cancellation is the one recorded by the Platform, in Lomé time (GMT).</N>
              <N n="11.3"><strong>Cancellation by the provider:</strong> the customer is fully refunded, service fee included, and KWA-BA helps them find an equivalent solution (article 12).</N>
              <N n="11.4"><strong>Exceptional circumstances:</strong> the customer is fully refunded, service fee included, if the service becomes impossible or prohibited for one of the following reasons, occurring after booking and substantiated: natural disaster; epidemic declared by the authorities with travel restrictions; border closure; official travel ban; curfew or serious unrest in the area; death or serious hospitalisation of the customer or a close relative, with proof. Instead of a refund, the customer may choose a credit. Not covered: ordinary flight delays or cancellations, visa difficulties known at booking, illnesses without hospitalisation, and events known at the booking date.</N>
              <N n="11.5">Refunds are made to the original payment method within <strong>seven business days</strong>. This period applies to refunds after a cancellation; it is distinct from the ten-working-day withdrawal period (article 10.1). If this is not possible, they are made to a Mobile Money account in the customer’s name, with their agreement. If the payment provider is unavailable, KWA-BA informs the customer and refunds as soon as the service is restored or by another means, within the time limits set by law.</N>
            </>
          ),
        },
        {
          id: "garantie",
          titre: "Kwa-Ba Guarantee",
          contenu: (
            <>
              <table>
                <thead><tr><th>Situation</th><th>KWA-BA commitment</th><th>Condition</th></tr></thead>
                <tbody>
                  <tr><td>Accommodation very different from the listing, unsanitary, dangerous or inaccessible</td><td>Equivalent rehousing or refund of unused nights and service fee</td><td>Report within <strong>24 hours of arrival</strong>, with photos</td></tr>
                  <tr><td>Major problem during the stay (water, electricity, safety, essential advertised equipment) not fixed by the host within 24 hours</td><td>Proportional refund of the nights concerned, or rehousing</td><td>Report within 24 hours of discovery</td></tr>
                  <tr><td>Cancellation by the host, accommodation already occupied (overbooking)</td><td>Equivalent rehousing or full refund</td><td>–</td></tr>
                  <tr><td>Driver or vehicle absent, more than one hour late or unable to come</td><td>Search for a replacement; failing that, refund of the day or trip</td><td>Immediate report</td></tr>
                  <tr><td>Vehicle different from the listing or in poor condition</td><td>Replacement or refund</td><td>Report before departure, with photos</td></tr>
                  <tr><td>Dispute over a security deposit</td><td>KWA-BA arbitration on the evidence (articles 13 and 14)</td><td>Report within 7 days</td></tr>
                </tbody>
              </table>
              <p>The Kwa-Ba Guarantee does not cover: differences in taste or opinion; incidents caused by the customer; services or payments made outside the Platform; lost or stolen personal belongings; indirect damage (missed flights, other bookings).</p>
              <p>Any refund granted under the Guarantee is capped at the total price of the booking concerned, unless the law provides otherwise.</p>
            </>
          ),
        },
        {
          id: "sejour",
          titre: "Stay rules",
          contenu: (
            <>
              <N n="13.1">The customer complies with the listing rules: check-in and check-out times; maximum number of people; pets; smoking; noise; parties and events, forbidden without written permission; visitors. Any undeclared person may be refused or charged as stated on the listing.</N>
              <N n="13.2">The customer shows an identity document to the provider if requested for the guest register.</N>
              <N n="13.3">A departure after the scheduled time without the host’s agreement may be charged according to the scale shown on the listing, up to one night.</N>
              <N n="13.4"><strong>Illegal activities</strong>: prostitution, drugs, weapons, hosting unaccompanied minors, serious disturbance. They lead to the immediate end of the stay without refund and may be reported to the authorities.</N>
              <N n="13.5"><strong>Security deposit for accommodation</strong>: the host may request one provided it is shown on the listing before booking. It is limited to one night and to 50,000 F CFA at most. It is handed over on arrival against a receipt and returned on departure, or at the latest within 48 hours. If damage is declared under article 13.6, the host only keeps the corresponding amount, pending KWA-BA’s opinion. No other deposit may be required.</N>
              <N n="13.6"><strong>Damage caused by the customer.</strong> The host declares damage within <strong>48 hours</strong> of departure, through the Platform, with photos and a quote or invoice. The customer has <strong>72 hours</strong> to reply. Failing agreement, KWA-BA gives a reasoned opinion, taking normal wear and tear into account. The amount retained is first taken from any security deposit. The balance is paid by the customer within 7 days through the Platform; otherwise KWA-BA may suspend their account and the host keeps its remedies.</N>
            </>
          ),
        },
        {
          id: "mobilite",
          titre: "Mobility rules",
          contenu: (
            <>
              <N n="14.1"><strong>Driver (without chauffeur)</strong>: at least <strong>23 years old</strong>; driving licence held for at least <strong>2 years</strong> and valid in Togo; international licence or translation if required. The owner may set stricter conditions on the listing. Only drivers declared at booking may drive.</N>
              <N n="14.2"><strong>Check-in and check-out inspection</strong>: at departure and return, the customer and the owner photograph the vehicle (body, interior, odometer, fuel level). A defect not recorded at departure is presumed to have occurred during the rental, unless proven otherwise.</N>
              <N n="14.3"><strong>Security deposit (without driver only)</strong>:</N>
              <ul>
                <li>when publishing, the owner chooses between no deposit (“No deposit” badge), one day of rental or two days, up to 100,000 F CFA;</li>
                <li>the deposit is halved for a customer who has completed 3 rentals without incident;</li>
                <li>it is <strong>paid online with the rental and held by KWA-BA</strong> during the rental; the owner does not ask for any deposit when handing over the keys;</li>
                <li>the owner reports any damage, missing fuel or delay, with photos, within 24 hours of the vehicle’s return; the deposit, minus any deductions, is refunded to the customer <strong>within 48 hours</strong> of the return;</li>
                <li>only the amounts on the displayed scale (missing fuel, delay, abnormal cleaning, minor damage) or those justified by the inspection and a quote may be deducted;</li>
                <li>in case of disagreement, KWA-BA arbitrates and may hold the disputed amount until the dispute is settled.</li>
              </ul>
              <p>No deposit is required for a rental with driver.</p>
              <N n="14.4"><strong>Fuel</strong>: the vehicle is returned with the same fuel level as at departure. Otherwise, the missing fuel is charged at the pump price, plus a 2,000 F CFA service charge.</N>
              <N n="14.5"><strong>Late return</strong>: 30 minutes’ grace. Beyond that, each hour of delay is charged at 10% of the daily price; beyond 3 hours, a full day is due. The customer informs the owner as soon as they expect a delay.</N>
              <N n="14.6"><strong>Prohibited uses</strong>: driving under the influence of alcohol or drugs; undeclared driver; subletting; carrying people or goods for payment; racing and unauthorised off-road use; towing; carrying dangerous or illegal goods; leaving Togo without the owner’s written agreement and without insurance covering the countries visited (ECOWAS brown card).</N>
              <N n="14.7"><strong>Fines, tolls and parking</strong>: payable by the customer for the whole duration of a rental without driver. With a driver, driving offences are payable by the driver, unless they result from the customer’s request.</N>
              <N n="14.8"><strong>Accident, breakdown, theft</strong>: the customer immediately informs the owner and KWA-BA, and at the latest within <strong>24 hours</strong>; they fill in an accident report or have the facts recorded by the police or gendarmerie, and do not admit liability alone; in case of theft, they file a complaint and hand over the keys and papers; in case of a breakdown not attributable to the customer, the owner replaces the vehicle or refunds the unused days.</N>
              <N n="14.9"><strong>Insurance and customer liability</strong>: the owner must insure the vehicle for rental (compulsory third-party liability and, where applicable, damage) and show on the listing the excess payable by the driver. For damage occurring during a rental without driver, the customer’s liability is limited to this excess, except in case of gross misconduct: alcohol, drugs, undeclared driver, prohibited use, or failure to report within 24 hours. In case of gross misconduct, the customer is liable for the full damage.</N>
              <N n="14.10"><strong>Driver</strong>: working day of up to 10 hours, with reasonable breaks; the driver may refuse any request contrary to the law, safety or the highway code; the customer remains responsible for their personal belongings. <strong>Driver for the customer’s vehicle</strong>: the customer guarantees that their vehicle is roadworthy and in order (papers, technical inspection) and that their insurance covers driving by a third party; otherwise the driver may refuse the mission and the customer is not refunded.</N>
            </>
          ),
        },
        {
          id: "longue-duree",
          titre: "Long-term rental",
          contenu: <p>Finding a home to rent long term (visits, introductions, inventory) is not open yet. Its conditions will be published when it opens.</p>,
        },
        {
          id: "plateforme",
          titre: "Booking through the Platform",
          contenu: (
            <>
              <N n="16.1">For a new stay or rental with a provider discovered on the Platform, the customer books again through the Platform. They then benefit from the Loyal customer rate (3%) or the “My driver” feature, and keep the Kwa-Ba Guarantee. The “My driver” feature lets the customer ask again for a driver they have already had through the Platform: that driver then receives 6,500 CFA francs per day instead of 6,000, and KWA-BA keeps 500 CFA francs instead of 1,000. The price paid by the customer does not change.</N>
              <N n="16.2">A customer who receives an offer to pay or book outside the Platform may report it to KWA-BA. A verified report is rewarded with 5,000 F CFA.</N>
            </>
          ),
        },
        {
          id: "avis",
          titre: "Reviews",
          contenu: (
            <>
              <N n="17.1">Only customers who actually received a service may publish a review, within 14 days of its end.</N>
              <N n="17.2">The review must be honest, personal and respectful. Insulting, defamatory or discriminatory remarks and personal data of third parties are forbidden.</N>
              <N n="17.3">KWA-BA moderates reviews according to the <Link href="/cgu#avis">review charter in the terms of use</Link>. It does not publish paid reviews or reviews written by the provider. The provider has a right of reply.</N>
            </>
          ),
        },
        {
          id: "suspension",
          titre: "Account suspension",
          contenu: (
            <>
              <N n="18.1">KWA-BA may suspend an account in the event of a serious breach of the Terms of Sale: fraud, payment outside the Platform, violence, repeated damage, fake reviews, illegal activity.</N>
              <N n="18.2">Except in an emergency related to safety or fraud, the customer is first informed of the facts and has 7 days to explain.</N>
              <N n="18.3">Suspension does not affect bookings already paid, except in case of fraud or safety risk; such bookings are then cancelled and refunded, minus any sums owed by the customer.</N>
            </>
          ),
        },
        {
          id: "responsabilite",
          titre: "Liability",
          contenu: (
            <>
              <N n="19.1">KWA-BA is liable for the proper performance of its own services (article 3.3), subject to the mandatory legal provisions applicable to e-commerce.</N>
              <N n="19.2">The provider is liable for the performance of its service. KWA-BA has recourse against it for any sum it has paid in its place.</N>
              <N n="19.3">Except in the event of gross or intentional misconduct by KWA-BA, bodily injury or contrary legal provision, its liability for its own service is limited to the service fees received for the booking concerned. This cap does not apply to the Kwa-Ba Guarantee, which follows its own rules.</N>
              <N n="19.4">Neither party is liable for a failure due to force majeure, i.e. an unforeseeable, irresistible and external event.</N>
              <N n="19.5">KWA-BA uses reasonable means to ensure access to the Platform, without guaranteeing permanent availability.</N>
            </>
          ),
        },
        {
          id: "donnees",
          titre: "Personal data",
          contenu: (
            <>
              <N n="20.1">KWA-BA processes the customer’s data in accordance with law no. 2019-014 of 29 October 2019 on the protection of personal data and its <Link href="/confidentialite">privacy policy</Link>. Declaration to the IPDCP no. <MentionSociete cle="ipdcp" libelle="declaration number" />.</N>
              <N n="20.2">Only the data necessary for the service are passed on to the provider.</N>
              <N n="20.3">The customer has a right of access, rectification, objection and erasure, to be exercised at <LienContact sujet="My personal data" />. They may also refer the matter to the IPDCP.</N>
              <N n="20.4">They may object at any time, free of charge, to receiving commercial messages (law no. 2017-07, art. 37), through the link in each message or from their account.</N>
              <N n="20.5">Data may be hosted or accessed outside Togo, in particular by the partners based in France and by the payment provider (FedaPay, based in Benin), in compliance with the transfer conditions provided by law. The payment provider processes payment data under its own responsibility, for payment and fraud prevention purposes.</N>
            </>
          ),
        },
        {
          id: "reclamations",
          titre: "Complaints, mediation and disputes",
          contenu: (
            <>
              <N n="21.1">Any complaint is sent to KWA-BA through the Platform or to <LienContact sujet="Complaint" />. KWA-BA acknowledges receipt within 72 hours.</N>
              <N n="21.2">In the event of a disagreement with a provider, KWA-BA offers free mediation and gives a written opinion within 10 days, based on the documents provided by each party.</N>
              <N n="21.3">The parties seek an amicable solution for 30 days before any legal action, except in an emergency.</N>
            </>
          ),
        },
        {
          id: "preuve",
          titre: "Evidence and retention",
          contenu: (
            <>
              <N n="22.1">Data recorded by the Platform are binding between the parties unless proven otherwise: bookings, payments, messages, mission codes, time-stamped photos, receipts. In accordance with law no. 2017-07, electronic documents have the same evidential value as paper documents.</N>
              <N n="22.2">KWA-BA keeps contracts concluded electronically for at least 5 years after their performance, or longer where the law requires, and gives the customer access to them on request.</N>
            </>
          ),
        },
        {
          id: "divers",
          titre: "Miscellaneous",
          contenu: (
            <>
              <N n="23.1">KWA-BA may amend the Terms of Sale. The applicable version is the one accepted at booking. Any significant change is announced at least 30 days in advance to customers with an account.</N>
              <N n="23.2">If a clause is declared void, the others remain applicable.</N>
              <N n="23.3">Failure to rely on a clause does not constitute a waiver of it.</N>
              <N n="23.4">Communications between the parties take place through the Platform or by email, using the account details.</N>
            </>
          ),
        },
        {
          id: "droit",
          titre: "Governing law and jurisdiction",
          contenu: (
            <>
              <N n="24.1">These terms are governed by Togolese law and the OHADA uniform acts, without depriving the consumer of the mandatory provisions of the country where they reside.</N>
              <N n="24.2">Failing an amicable solution, any dispute falls within the jurisdiction of the competent courts of Lomé, in particular the Lomé commercial court for professional customers.</N>
            </>
          ),
        },
        {
          id: "annexe-1",
          numero: "",
          titre: "Annex 1 – Cancellation and refund policy",
          contenu: (
            <>
              <p>The free 48-hour cooling-off period (article 10.3) and the rules of articles 11.3 and 11.4 apply in addition to the tables below.</p>
              <p className="font-semibold text-dark">Short-term accommodation (the host chooses one of three options, shown on the listing)</p>
              <AccommodationTable />
              <ul>
                <li><strong>Stays of 28 nights or more:</strong> the first month is non-refundable if cancelled less than 30 days before arrival; the following months are refunded if the customer gives at least 30 days’ notice.</li>
                <li><strong>No-show without cancellation:</strong> no refund.</li>
                <li><strong>Cleaning fee:</strong> refunded if the customer has not arrived.</li>
                <li><strong>Hotels:</strong> the hotel’s own policy, shown before booking, applies if it is more favourable to the customer.</li>
              </ul>
              <p className="font-semibold text-dark">Mobility</p>
              <MobilityTable />
              <p>In the event of late cancellation, the driver’s share is paid to them. If a flight is delayed, the customer informs the driver; waiting beyond one hour may be charged as overtime.</p>
            </>
          ),
        },
        {
          id: "annexe-2",
          numero: "",
          titre: "Annex 2 – Summary of customer prices",
          contenu: (
            <table>
              <thead><tr><th>Service</th><th>What the customer pays</th></tr></thead>
              <tbody>
                <tr><td>Short stay</td><td>Price of nights + 6% (3% with the Stay Pack or as a Loyal customer, 4% for companies under a framework agreement)</td></tr>
                <tr><td>Car</td><td>Price set by the owner, no service fee</td></tr>
                <tr><td>Airport transfer</td><td>Flat price per trip, driver included</td></tr>
                <tr><td>Driver</td><td>7,000 F CFA per day + any allowances (1,500 or 2,000 F CFA per day) + overtime (1,000 F CFA)</td></tr>
              </tbody>
            </table>
          ),
        },
      ]}
    />
  );
}

/** Accommodation cancellation scale (annex 1), also shown on the “Cancellation and refund” page. */
export function AccommodationTable() {
  return (
    <table>
      <thead><tr><th>Option</th><th>Cancellation by the customer</th><th>Refund</th></tr></thead>
      <tbody>
        <tr><td><strong>Flexible</strong></td><td>Up to 24 hours before arrival</td><td>Full, service fee included</td></tr>
        <tr><td></td><td>Less than 24 hours before</td><td>First night kept, rest refunded; service fee kept</td></tr>
        <tr><td><strong>Moderate</strong></td><td>Up to 5 days before arrival</td><td>Full, service fee included</td></tr>
        <tr><td></td><td>Between 5 days and 24 hours before</td><td>50% of the nights; service fee kept</td></tr>
        <tr><td></td><td>Less than 24 hours before</td><td>No refund</td></tr>
        <tr><td><strong>Strict</strong></td><td>Up to 30 days before arrival</td><td>Full, service fee included</td></tr>
        <tr><td></td><td>Between 30 and 7 days before</td><td>50% of the nights; service fee kept</td></tr>
        <tr><td></td><td>Less than 7 days before</td><td>No refund</td></tr>
      </tbody>
    </table>
  );
}

/** Mobility cancellation scale (annex 1). */
export function MobilityTable() {
  return (
    <table>
      <thead><tr><th>Service</th><th>Cancellation by the customer</th><th>Refund</th></tr></thead>
      <tbody>
        <tr><td>Airport transfer</td><td>Up to 24 hours before</td><td>Full</td></tr>
        <tr><td></td><td>Less than 24 hours before</td><td>No refund</td></tr>
        <tr><td>Car with or without driver, driver only</td><td>Up to 48 hours before</td><td>Full</td></tr>
        <tr><td></td><td>Between 48 and 24 hours before</td><td>50%</td></tr>
        <tr><td></td><td>Less than 24 hours before</td><td>No refund</td></tr>
      </tbody>
    </table>
  );
}
