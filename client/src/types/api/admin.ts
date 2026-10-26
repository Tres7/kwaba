import type { StatutContrat, TypeContrat } from "./contrat";

// Contrat : documentation/modules/backoffice-api.md

export interface AdminPage<T> {
  results: T[];
  count: number;
  page: number;
  page_size: number;
}

export interface AdminStats {
  utilisateurs: { total: number; nouveaux_30j: number; hotes: number; desactives: number };
  /** en_attente: waiting for an agent's visit (refused listings wait for their host). */
  annonces: { total: number; visibles: number; verifiees: number; en_attente: number };
  reservations: { confirmees_30j: number; annulees_30j: number; volume_30j: number };
  avis: { total: number; moyenne: number | null };
  reservations_par_jour: { date: string; nombre: number; volume: number }[];
}

export type Role = "voyageur" | "hote" | "agent" | "admin";

export interface AdminUser {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: Role;
  phone: string | null;
  avatar_url: string | null;
  is_verified: boolean;
  is_active: boolean;
  date_joined: string;
  last_login: string | null;
  nb_reservations: number;
  nb_annonces: number;
  /** Hosts only: commission set by the team. */
  conditions: ConditionsHote | null;
}

export interface ConditionsHote {
  categorie: "particulier" | "hotel";
  fondateur_debut: string | null;
  fondateur_fin: string | null;
  /** Rate applied today: 8, 12 (hotel) or 5 (Founders Programme). */
  commission_pourcent: number;
}

export interface AdminHebergement {
  id: string;
  name: string;
  type: string;
  city: string;
  location: string;
  price_per_night: number;
  image_url: string;
  is_available: boolean;
  /** Verified by an agent (or validated by an admin): only a verified and visible listing is published. */
  est_verifie: boolean;
  statut_verification: "en_attente" | "verifiee" | "refusee";
  rating: number;
  review_count: number;
  nb_reservations: number;
  host: { id: string; nom: string; email: string };
  created_at: string;
}

export interface AdminReservation {
  id: string;
  reference: string;
  hebergement: { id: string; name: string; city: string };
  voyageur: { id: string; nom: string; email: string };
  hote: { id: string; nom: string };
  check_in: string;
  check_out: string;
  nights: number;
  guests_count: number;
  total_price: number;
  status: "pending" | "confirmed" | "cancelled";
  payment_method: "mobile_money" | "carte" | "paypal";
  created_at: string;
}

export interface AdminAvis {
  id: string;
  note: number;
  commentaire: string;
  auteur: { id: string; nom: string; email: string };
  hebergement: { id: string; name: string };
  reponse_hote: string;
  created_at: string;
}

// --- Location de voiture (back-office) ---------------------------------------------------------

export interface ReglesLocation {
  commission_pourcent: string;
  delai_min_jours: number;
  duree_max_jours: number;
  annulation_gratuite_heures: number;
  conditions: string;
  caution_en_ligne: boolean;
  restitution_caution_heures: number;
}

export type CategorieExperience = "activites" | "restaurants" | "loisirs" | "sites";

/** Experience of the Discover page, as managed by the back-office (French and English texts). */
export interface ExperienceAdmin {
  id: number;
  categorie: CategorieExperience;
  nom: string;
  nom_en: string;
  etiquette: string;
  etiquette_en: string;
  ville: string;
  pays: string;
  pays_en: string;
  description: string;
  description_en: string;
  prix: number | null;
  gratuit: boolean;
  /** Displayed photo (uploaded from the back-office, or external for the original guide). */
  photo: string | null;
  actif: boolean;
  ordre: number;
}

export interface PhotoVehicule {
  id: number;
  url: string;
}

/** Vehicle of a partner owner (historical technical name: category). */
export interface CategorieVehicule {
  id: number;
  nom: string;
  gamme: "citadine" | "berline" | "suv" | "4x4" | "minibus" | "utilitaire";
  exemple_modele: string;
  description: string;
  places: number;
  bagages: number;
  boite: "manuelle" | "automatique";
  carburant: "essence" | "diesel" | "hybride" | "electrique";
  climatisation: boolean;
  /** The first one is the main photo. */
  photos: PhotoVehicule[];
  proprietaire: number | null;
  /** Vehicle price per day, set by the owner (without the driver). */
  prix_jour: number | null;
  sans_chauffeur: boolean;
  avec_chauffeur: boolean;
  /** Deposit chosen by the owner: 0, one or two days. */
  caution_jours: 0 | 1 | 2;
  /** Computed: days × price per day, 100,000 FCFA at most. */
  caution: number;
  immatriculation: string;
  annee: number | null;
  assurance_fin: string | null;
  visite_technique_fin: string | null;
  actif: boolean;
  ordre: number;
}

export interface LieuRemise {
  id: number;
  nom: string;
  ville: string;
  fuseau: "Africa/Lome" | "Africa/Porto-Novo";
  adresse_requise: boolean;
  frais: number;
  actif: boolean;
  ordre: number;
}

export interface Loueur {
  id: number;
  nom: string;
  contact: string;
  telephone: string;
  email: string;
  categories: number[];
  lieux: number[];
  actif: boolean;
  fondateur_debut: string | null;
  fondateur_fin: string | null;
  pays_versement: string;
  operateur_versement: string;
  numero_versement: string;
  nb_locations: number;
  nb_vehicules: number;
  /** Rate applied today: 15, 10 (founder) or 12 (Loyal Owner). */
  commission_pourcent: number | null;
}

export interface AdminLocation {
  id: string;
  reference: string;
  statut: "en_attente_paiement" | "confirmee" | "partenaire_assigne" | "terminee" | "annulee";
  statut_libelle: string;
  voyageur: { nom: string; email: string };
  telephone: string;
  categorie: string;
  formule: "sans_chauffeur" | "avec_chauffeur" | "chauffeur_seul";
  formule_libelle: string;
  proprietaire_vehicule: number | null;
  jours_hors_lome: number;
  jours_hors_pays: number;
  prix_vehicule: number;
  prix_chauffeur: number;
  primes: number;
  commission: number;
  part_kwaba_chauffeur: number;
  chauffeur_demande: { id: number; nom: string } | null;
  chauffeur_partenaire: { id: number; nom: string } | null;
  lieu_prise: string;
  adresse_prise: string;
  lieu_retour: string;
  adresse_retour: string;
  debut: string;
  fin: string;
  jours: number;
  passagers: number;
  prix: number;
  caution: number;
  caution_en_ligne: boolean;
  caution_retenue: number;
  caution_motif: string;
  caution_restituee_le: string | null;
  precisions: string;
  conducteur: string;
  permis_numero: string;
  permis_pays: string;
  partenaire: { id: number; nom: string } | null;
  vehicule: string;
  immatriculation: string;
  chauffeur_nom: string;
  chauffeur_telephone: string;
  cree_le: string;
}

// --- Airport transfers (back-office) ---------------------------------------------------------

export type CategorieTransfert = "berline" | "confort" | "van";

export interface AeroportAdmin {
  code: string;
  nom: string;
  ville: string;
  pays: string;
  fuseau: string;
  actif: boolean;
  tarifs: { categorie: CategorieTransfert; prix: number; actif: boolean }[];
}

export interface ChauffeurAdmin {
  id: number;
  prenom: string;
  nom: string;
  telephone: string;
  email: string;
  aeroports: string[];
  categorie: CategorieTransfert;
  vehicule: string;
  immatriculation: string;
  actif: boolean;
  /** "Excellence Driver" status: 6,500 FCFA per day instead of 6,000. */
  excellence: boolean;
  pays_versement: string;
  operateur_versement: string;
  numero_versement: string;
  nb_transferts: number;
}

/** Assignment choices of a rental: vehicle owners and partner drivers. */
export interface ChoixAttribution {
  partenaires: { id: number; nom: string; telephone: string }[];
  chauffeurs: { id: number; nom: string; telephone: string; excellence: boolean; demande: boolean }[];
}

export interface AdminTransfert {
  id: string;
  reference: string;
  statut: "en_attente_paiement" | "confirme" | "chauffeur_assigne" | "termine" | "annule";
  statut_libelle: string;
  voyageur: { nom: string; email: string };
  telephone: string;
  aeroport: { code: string; ville: string };
  arrivee: string;
  numero_vol: string;
  passagers: number;
  bagages: number;
  categorie: CategorieTransfert;
  categorie_libelle: string;
  destination: string;
  message: string;
  prix: number;
  majoration_nuit: boolean;
  chauffeur: { id: number; nom: string; telephone: string; vehicule: string } | null;
  cree_le: string;
}

// --- Kwa-Ba Give (back-office) -----------------------------------------------------------------

export type CauseGive = "education" | "sante" | "eau" | "environnement";

export interface OngAdmin {
  id: string;
  nom: string;
  slug: string;
  cause: CauseGive;
  pays: string;
  ville: string;
  resume: string;
  description: string;
  logo: string | null;
  image: string | null;
  site_web: string;
  numero_enregistrement: string;
  verifiee_le: string | null;
  verification: string;
  contact_nom: string;
  contact_email: string;
  contact_telephone: string;
  coordonnees_reversement: string;
  actif: boolean;
  collecte: number;
  nb_dons: number;
  nb_projets: number;
}

export interface ProjetAdmin {
  id: string;
  organisation: string;
  titre: string;
  cause: CauseGive;
  resume: string;
  description: string;
  lieu: string;
  objectif: number | null;
  image: string | null;
  actif: boolean;
}

export interface ReversementAdmin {
  id: string;
  reference: string;
  organisation: { id: string; nom: string };
  coordonnees_reversement: string;
  periode: string;
  montant: number;
  nb_dons: number;
  date_prevue: string;
  statut: "a_effectuer" | "effectue";
  statut_libelle: string;
  moyen: string;
  reference_operation: string;
  note: string;
  effectue_le: string | null;
  justificatif: string | null;
}

export interface DonAdmin {
  id: string;
  reference: string;
  donateur: { nom: string; email: string };
  organisation: string;
  projet: string | null;
  montant: number;
  total: number;
  montant_ong: number;
  moyen: string;
  statut: "en_attente" | "paye" | "echoue";
  statut_libelle: string;
  paye_le: string | null;
  cree_le: string;
}

export interface SocieteAdmin {
  raison_sociale: string;
  nom_commercial: string;
  forme_juridique: string;
  adresse: string;
  pays: string;
  nif: string;
  rccm: string;
  telephone: string;
  email: string;
  site: string;
  assujetti_tva: boolean;
  taux_tva: string;
  mentions: string;
  representant_nom: string;
  representant_qualite: string;
  complets: boolean;
  signature_presente: boolean;
}

export interface FactureAdmin {
  id: string;
  numero: string;
  emise_le: string;
  objet_type: "reservation" | "transfert" | "location" | "libre";
  objet_libelle: string;
  objet_id: string | null;
  client_nom: string;
  client_email: string;
  total_ttc: number;
  tva: number;
}

export interface ContratAdmin {
  id: string;
  reference: string;
  type: TypeContrat;
  type_libelle: string;
  titre: string;
  statut: StatutContrat;
  statut_libelle: string;
  partie_nom: string;
  partie_email: string;
  partie_telephone: string;
  cree_le: string;
  envoye_le: string | null;
  expire_le: string;
  expire: boolean;
  signe_le: string | null;
  signataire_nom: string;
  ip: string | null;
  methode: string;
  empreinte_pdf: string;
  motif_annulation: string;
  version_modele: number;
}

export interface PartieContrat {
  id: string;
  nom: string;
  email: string;
  contrat: StatutContrat | null;
}

export interface ModeleContrat {
  type: TypeContrat;
  type_libelle: string;
  titre: string;
  corps: string;
  version: number;
  modifie_le: string;
}

export interface AlerteFraude {
  id: number;
  cree_le: string;
  contexte: "message" | "annonce";
  contexte_libelle: string;
  objet_id: string;
  types: string[];
  extraits: string[];
  masquee: boolean;
  traitee: boolean;
  traitee_le: string | null;
  note: string;
  utilisateur: { id: string; nom: string; email: string; role: string; nb_alertes: number | null };
}
