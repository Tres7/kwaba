/** Help centre in English (same sections and order as the French version in page.tsx, which prevails). */
export const SECTIONS_EN = [
  {
    id: "reservations",
    title: "Bookings",
    items: [
      { q: "How do I book a place?", a: "Choose your dates and number of guests on the listing page, then click “Book”. Before paying you see a full summary: detailed price in CFA francs, cancellation policy, house rules (terms of sale, art. 5.1). You accept the terms of sale by ticking a box, then pay. The booking is firm once payment is confirmed (art. 5.2 and 5.3)." },
      { q: "Can I book if the place is already taken?", a: "No. Once a booking is confirmed, its dates are blocked with the provider, who turns away other customers for those dates (terms of sale, art. 10.2). A search with dates therefore only shows places available for that period." },
      { q: "How do I contact my host?", a: "Through Kwa-Ba messaging, before and after payment (terms of sale, art. 5.4): “Contact” button on the listing, then “Messages”. Messages stay polite and related to the stay (terms of use, art. 6.1). Never pay the host outside the Platform: you would lose the Kwa-Ba Guarantee (terms of use, art. 6.2)." },
    ],
  },
  {
    id: "annulation",
    title: "Cancellation",
    items: [
      { q: "How do I cancel a booking?", a: "In Profile → My bookings, click “Cancel”. The time used is the one recorded by the Platform, Lomé time (terms of sale, art. 11.2). The refund follows the policy chosen by the host (Flexible, Moderate or Firm), shown on the listing (annex 1). A booking cancelled within 48 hours of confirmation and at least 7 days before arrival is refunded in full, service fee included (art. 10.3)." },
      { q: "Can I cancel a stay that has started?", a: "Leaving early gives no right to a refund, unless the host agrees or the Kwa-Ba Guarantee applies (terms of sale, art. 9.3). If the place is very different from the listing, unsanitary, dangerous or inaccessible, report it within 24 hours of arrival with photos: Kwa-Ba rehouses you or refunds the unused nights (art. 12)." },
    ],
  },
  {
    id: "paiement",
    title: "Payment",
    items: [
      { q: "Which payment methods are accepted?", a: "Payments go through FedaPay, a payment institution licensed by the BCEAO: Mobile Money (Moov Money/Flooz, Mixx by Yas/T-Money) or Visa or Mastercard card (terms of sale, art. 7.1). You always pay in CFA francs (art. 7.3); a price shown in euros is only an indicative equivalent. Never pay a provider in cash, except a holding deposit for a place handed over against a receipt (art. 7.5)." },
      { q: "When am I charged?", a: "When you book, on FedaPay's secure page; Kwa-Ba does not keep your full card details (terms of sale, art. 7.1). The booking is firm once payment is confirmed; the confirmation is sent immediately, and within five days at the latest (art. 5.3). The price cannot be increased afterwards (art. 6.2)." },
      { q: "When is the host paid?", a: "Kwa-Ba keeps the price until 24 hours after your arrival, then pays it to the host (terms of sale, art. 8.1). This gives you time to report a problem before the host is paid (art. 8.3)." },
      { q: "How am I refunded?", a: "To the original payment method, within seven business days; failing that, to a Mobile Money account in your name, with your agreement (terms of sale, art. 11.5). The amount depends on the listing's cancellation policy (annex 1). If the provider cancels, you are refunded in full, service fee included (art. 11.3)." },
      { q: "What does the service fee cover?", a: "It pays for Kwa-Ba's booking service and support (terms of sale, art. 2 and 3.3). It is 6% of the price of the nights; 3% for a loyal customer returning to the same host or for a Stay + Driver Pack (art. 6.4). Reductions are not cumulative, and the breakdown is shown before payment (art. 5.1)." },
    ],
  },
  {
    id: "transferts",
    title: "Airport transfer",
    items: [
      { q: "How do I book a driver at the airport?", a: "From “Airport transfer”: enter your flight, the number of passengers and bags, choose the vehicle, then pay. The price is a flat rate per trip, depending on the airport and vehicle category, driver included, the same by day and by night (terms of sale, art. 6.5)." },
      { q: "When will I know who my driver is?", a: "The driver's name and number are sent to you once the driver is assigned, at the latest 24 hours before pick-up (terms of sale, art. 5.4). If the driver does not show up or is more than an hour late, Kwa-Ba looks for a replacement or refunds the trip (art. 12)." },
      { q: "My flight is delayed: what should I do?", a: "Let the driver know as soon as possible, on the number sent with your transfer (terms of sale, art. 5.4). Waiting beyond one hour may be charged as overtime, 1,000 CFA francs per hour (annex 1 and art. 6.5). An ordinary flight delay does not give a right to a refund for exceptional circumstances (art. 11.4)." },
      { q: "Can I cancel?", a: "Yes: a transfer cancelled up to 24 hours before is refunded in full; less than 24 hours before, it is no longer refunded (terms of sale, annex 1). The cooling-off period also applies: cancelled within 48 hours of booking and at least 7 days before the trip, it is refunded in full (art. 10.3)." },
    ],
  },
  {
    id: "compte",
    title: "My account",
    items: [
      // Not in the terms: how the site works
      { q: "I didn't receive my verification code", a: "Check your spam folder, then use “Resend code” on the verification page (a new code every 60 seconds). The code is valid for 10 minutes." },
      { q: "I forgot my password", a: "Click “Forgot password?” on the sign-in page: a code is emailed to you to choose a new password. Keep your login details confidential and tell Kwa-Ba in case of fraudulent use (terms of use, art. 4.3)." },
      { q: "How do I become a host?", a: "From “Become a host”, activate your host account, then prepare your listing in the Host area. Only a registered partner who has accepted the terms that apply to them may publish (terms of use, art. 5.1). Before publication, Kwa-Ba checks your identity and documents and visits the place (art. 5.2). The listing must be accurate and contain no personal contact details (art. 5.3 and 5.4)." },
      { q: "How do I change the language?", a: "Use the FR / EN switch at the top of the page or in the footer, or go to Profile → Language & region; your choice is remembered on this device. The terms of sale are written in French, which prevails over any translation (terms of sale, art. 1.4)." },
    ],
  },
  {
    id: "conditions",
    title: "Terms of use",
    items: [
      { q: "Guests' commitments", a: "Book with an accurate account, in your own name, as an adult (terms of use, art. 4.2; terms of sale, art. 4.1). Follow the house rules: times, number of people, noise, parties, visitors (terms of sale, art. 13.1), and show an ID if the host asks for it (art. 13.2). All payments go through the Platform (art. 7.5)." },
      { q: "Hosts' commitments", a: "Describe the offer accurately and completely: recent photos, amenities, rules, price in CFA francs, cancellation terms (terms of use, art. 5.3). Include no contact details that would allow dealing outside the Platform (art. 5.4). The host remains responsible for their service and its compliance with the listing (terms of sale, art. 3.2)." },
    ],
  },
  {
    id: "confidentialite",
    title: "Privacy",
    items: [
      { q: "What data is collected?", a: "Your account details (first and last name, email, phone, country of residence: terms of use, art. 4.2), your bookings, payments and messages, processed under law no. 2019-014 and the privacy policy (terms of use, art. 13.1). Only the data needed for the service is passed on to the provider (terms of sale, art. 20.2). You can access, correct or delete it (art. 20.3)." },
      // Not in the terms: how the site works
      { q: "Is my password protected?", a: "Yes: it is stored in encrypted (hashed) form and is never visible, not even to the Kwa-Ba team." },
    ],
  },
  {
    id: "reclamations",
    title: "Complaints",
    items: [
      { q: "How do I make a complaint?", a: "With the form at the bottom of this page or by email: Kwa-Ba acknowledges receipt within 72 hours (terms of sale, art. 21.1). In a disagreement with a provider, Kwa-Ba offers free mediation and gives a written opinion within 10 days (art. 21.2). An amicable solution is sought for 30 days before any legal action (art. 21.3)." },
    ],
  },
];
