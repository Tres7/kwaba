import type { GuidePays } from "./types";

const VOYAGE_GOUV = { libelle: "Official portal for travel to Togo (e-visa, entry requirements)", url: "https://voyage.gouv.tg" };
const CONSEILS_UK = {
  libelle: "UK Foreign Office travel advice for Togo",
  url: "https://www.gov.uk/foreign-travel-advice/togo",
};

/** English version of the French guide (the French one is authoritative). */
const togo: GuidePays = {
  code: "togo",
  nom: "Togo",
  titre: "Prepare your trip to Togo",
  description: "Visa, vaccines, money, arriving in Lomé, getting around, weather, where to stay: the essentials to prepare your stay in Togo.",
  intro: "Everything to know before you leave and when you land in Lomé, topic by topic.",
  misAJour: "Updated on 4 November 2026",
  avertissement: "Entry and health rules can change: check them before you leave on the official sites given here.",
  sommaire: "Contents",
  sourcesTitre: "Check on",
  rubriques: {
    formalites: {
      titre: "Passport and visa",
      icone: "passeport",
      points: [
        "A **passport valid for at least 6 months** after your arrival date.",
        "**ECOWAS** citizens do not need a visa.",
        "Other travellers apply for an **e-visa online before leaving**, on the official portal. Keep the confirmation with you.",
        "An address for your stay may be asked on arrival: your Kwa-Ba booking voucher will do.",
      ],
      sources: [VOYAGE_GOUV],
    },
    sante: {
      titre: "Health and vaccines",
      icone: "sante",
      points: [
        "A **yellow fever vaccination certificate** is required on arrival: bring your international certificate.",
        "**Malaria**: ask your doctor about preventive treatment; use a mosquito net and repellent in the evening.",
        "Drink **bottled water** and take **travel insurance** that covers repatriation.",
      ],
      sources: [CONSEILS_UK],
    },
    argent: {
      titre: "Money and payment",
      icone: "argent",
      points: [
        "The currency is the **CFA franc** (F CFA), pegged to the euro: **€1 = 655.957 F CFA**.",
        "**Mobile Money** is everywhere; **cards** are accepted in hotels and large shops.",
        "Keep some **cash** for markets and motorbike taxis. There are plenty of cash machines in Lomé.",
        "On Kwa-Ba, you pay **online, by Mobile Money or card**, before your stay.",
      ],
    },
    arriver: {
      titre: "Arriving in Lomé",
      icone: "avion",
      points: [
        "You land at **Gnassingbé Eyadéma International Airport** (LFW), about twenty minutes from the centre.",
        "The easiest way: a **driver waiting for you** at the exit, at a fixed price paid in advance.",
      ],
      action: { libelle: "Book my airport transfer", href: "/transfert" },
    },
    deplacements: {
      titre: "Getting around",
      icone: "deplacements",
      points: [
        "**Zémidjans** (motorbike taxis) and taxis are everywhere: **agree on the price before getting on**.",
        "Traffic drives on the right. For trips in town or to Kpalimé, Aného or Atakpamé, a **car with a driver** saves hassle.",
      ],
      action: { libelle: "Rent a car with a driver", href: "/location" },
    },
    telephone: {
      titre: "Phone and internet",
      icone: "telephone",
      points: [
        "Two operators: **Yas** and **Moov Africa**. You buy a SIM card with your **passport**.",
        "Mobile data plans are cheap.",
        "For your stay, write to the host through **Kwa-Ba messaging**: your exchanges stay protected.",
      ],
    },
    climat: {
      titre: "Weather and best time to go",
      icone: "climat",
      points: [
        "Tropical climate: **25 to 32 °C** all year round on the coast.",
        "**Dry season from November to March**; the harmattan, a dry and dusty wind, blows from December to February.",
        "In the south, **rainy seasons from April to July**, then in September and October.",
        "Lomé time: **GMT all year round**, no daylight saving.",
      ],
    },
    electricite: {
      titre: "Electricity",
      icone: "prise",
      points: [
        "**220 V** current, **type C and E** sockets (as in France).",
        "Power cuts can happen: in the search, filter the places with a **generator**.",
      ],
    },
    loger: {
      titre: "Where to stay in Lomé",
      icone: "logement",
      points: [
        "**The seaside** (Bè, Baguida, Avépozo) for the beach and some quiet.",
        "**Tokoin and the centre** to be close to everything.",
        "**Agoè**, in the north, more residential.",
        "Every Kwa-Ba place is **visited by an agent** before it is published.",
      ],
      action: { libelle: "See places to stay in Lomé", href: "/recherche?city=Lom%C3%A9" },
    },
    securite: {
      titre: "Safety",
      icone: "securite",
      points: [
        "Lomé is a calm capital: **usual precautions** are enough, especially at night.",
        "The **sea is dangerous** (strong currents): only swim where there are lifeguards.",
        "The **north of the country**, near the border with Burkina Faso, is subject to warnings: read your government's advice before going there.",
        "Emergencies: **police 117**, **fire brigade 118**.",
      ],
      sources: [CONSEILS_UK],
    },
    usages: {
      titre: "Customs and languages",
      icone: "usages",
      points: [
        "People **greet before asking anything**; give and take with the **right hand**.",
        "**Ask before photographing** someone; official and military buildings must not be photographed.",
        "At the market, people **bargain**, with a smile.",
        "**French** is the official language; **Ewe** is widely spoken in the south. \"**Woezɔ**\" means welcome, \"**Akpé**\" thank you.",
      ],
    },
  },
};

export default togo;
