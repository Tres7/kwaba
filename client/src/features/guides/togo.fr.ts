import type { GuidePays } from "./types";

const VOYAGE_GOUV = { libelle: "Portail officiel du voyage au Togo (e-visa, formalités)", url: "https://voyage.gouv.tg" };
const CONSEILS_FR = {
  libelle: "Conseils aux voyageurs du ministère français des Affaires étrangères",
  url: "https://www.diplomatie.gouv.fr/fr/conseils-aux-voyageurs/conseils-par-pays-destination/togo/",
};

/** French version (authoritative). To review with the team before publication, especially visa and health. */
const togo: GuidePays = {
  code: "togo",
  nom: "Togo",
  titre: "Préparer votre voyage au Togo",
  description: "Visa, vaccins, argent, arrivée à Lomé, transports, climat, quartiers où loger : l'essentiel pour préparer votre séjour au Togo.",
  intro: "Tout ce qu'il faut savoir avant de partir et en arrivant à Lomé, rubrique par rubrique.",
  misAJour: "Mis à jour le 4 novembre 2026",
  avertissement: "Les règles d'entrée et de santé peuvent changer : vérifiez-les avant le départ sur les sites officiels indiqués.",
  sommaire: "Sommaire",
  sourcesTitre: "À vérifier sur",
  rubriques: {
    formalites: {
      titre: "Passeport et visa",
      icone: "passeport",
      points: [
        "Un **passeport valable au moins 6 mois** après la date d'arrivée.",
        "Les ressortissants de la **CEDEAO** n'ont pas besoin de visa.",
        "Les autres voyageurs demandent un **e-visa en ligne avant le départ**, sur le portail officiel. Gardez la confirmation sur vous.",
        "Une adresse de séjour peut être demandée à l'arrivée : votre bon de réservation Kwa-Ba fait l'affaire.",
      ],
      sources: [VOYAGE_GOUV],
    },
    sante: {
      titre: "Santé et vaccins",
      icone: "sante",
      points: [
        "Le **certificat de vaccination contre la fièvre jaune** est exigé à l'arrivée : prenez votre carnet international.",
        "**Paludisme** : voyez avec votre médecin le traitement préventif ; moustiquaire et répulsif le soir.",
        "Buvez de l'**eau en bouteille** et prenez une **assurance voyage** qui couvre le rapatriement.",
      ],
      sources: [CONSEILS_FR],
    },
    argent: {
      titre: "Argent et paiement",
      icone: "argent",
      points: [
        "La monnaie est le **franc CFA** (F CFA), à parité fixe avec l'euro : **1 € = 655,957 F CFA**.",
        "Le **Mobile Money** est partout ; la **carte** est acceptée dans les hôtels et les grandes enseignes.",
        "Gardez des **espèces** pour les marchés et les taxis-motos. Les distributeurs sont nombreux à Lomé.",
        "Sur Kwa-Ba, vous payez **en ligne, par Mobile Money ou par carte**, avant le séjour.",
      ],
    },
    arriver: {
      titre: "Arriver à Lomé",
      icone: "avion",
      points: [
        "Vous atterrissez à l'**aéroport international Gnassingbé Eyadéma** (LFW), à une vingtaine de minutes du centre.",
        "Le plus simple : un **chauffeur qui vous attend** à la sortie, à prix fixe payé à l'avance.",
      ],
      action: { libelle: "Réserver mon transfert depuis l'aéroport", href: "/transfert" },
    },
    deplacements: {
      titre: "Se déplacer",
      icone: "deplacements",
      points: [
        "Les **zémidjans** (taxis-motos) et les taxis sont partout : **fixez le prix avant de monter**.",
        "On roule à droite. Pour vos trajets en ville ou vers Kpalimé, Aného ou Atakpamé, une **voiture avec chauffeur** évite les soucis.",
      ],
      action: { libelle: "Louer une voiture avec chauffeur", href: "/location" },
    },
    telephone: {
      titre: "Téléphone et internet",
      icone: "telephone",
      points: [
        "Deux opérateurs : **Yas** et **Moov Africa**. Une carte SIM s'achète avec votre **passeport**.",
        "Les forfaits internet mobiles sont bon marché.",
        "Pour votre logement, écrivez à l'hôte par la **messagerie Kwa-Ba** : vos échanges restent protégés.",
      ],
    },
    climat: {
      titre: "Climat et meilleure période",
      icone: "climat",
      points: [
        "Climat tropical : **25 à 32 °C** toute l'année sur la côte.",
        "**Saison sèche de novembre à mars** ; l'harmattan, vent sec et poussiéreux, souffle de décembre à février.",
        "Au sud, **saisons des pluies d'avril à juillet** puis en septembre-octobre.",
        "Heure de Lomé : **GMT toute l'année**, sans changement d'heure.",
      ],
    },
    electricite: {
      titre: "Électricité",
      icone: "prise",
      points: [
        "Courant **220 V**, prises **C et E** (comme en France).",
        "Des coupures sont possibles : dans la recherche, filtrez les logements avec **groupe électrogène**.",
      ],
    },
    loger: {
      titre: "Où loger à Lomé",
      icone: "logement",
      points: [
        "**Le bord de mer** (Bè, Baguida, Avépozo) pour la plage et le calme.",
        "**Tokoin et le centre** pour être près de tout.",
        "**Agoè**, au nord, plus résidentiel.",
        "Tous les logements Kwa-Ba sont **visités par un agent** avant d'être publiés.",
      ],
      action: { libelle: "Voir les logements à Lomé", href: "/recherche?city=Lom%C3%A9" },
    },
    securite: {
      titre: "Sécurité",
      icone: "securite",
      points: [
        "Lomé est une capitale calme : les **précautions habituelles** suffisent, surtout le soir.",
        "La **mer est dangereuse** (courants forts) : ne vous baignez qu'aux endroits surveillés.",
        "Le **nord du pays**, près de la frontière avec le Burkina Faso, fait l'objet d'avertissements : lisez les conseils de votre gouvernement avant d'y aller.",
        "Urgences : **police 117**, **pompiers 118**.",
      ],
      sources: [CONSEILS_FR],
    },
    usages: {
      titre: "Usages et langues",
      icone: "usages",
      points: [
        "On **salue avant toute demande** ; on donne et on reçoit de la **main droite**.",
        "**Demandez avant de photographier** quelqu'un ; les bâtiments officiels et militaires ne se photographient pas.",
        "Au marché, on **négocie**, avec le sourire.",
        "Le **français** est la langue officielle ; l'**éwé** est très parlé au sud. « **Woezɔ** » veut dire bienvenue, « **Akpé** » merci.",
      ],
    },
  },
};

export default togo;
