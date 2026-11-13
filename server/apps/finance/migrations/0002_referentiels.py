# Reference data of the finance module, copied from 07_Schema_base_de_donnees.sql (10 November 2026), sections 2.1 to
# 2.7, 5 and 9: offers, families, natures, money accounts, payment methods, kinds of third party, parameters, axes and
# reports. SYSCOHADA accounts are proposals to be confirmed by the chartered accountant; values at 0 wait for a
# decision of the partners. Changing a value later is a row of history, never a new migration of this file.
#
# One change from the file: the partner money natures that go up then down (T01 to T04, T06 to T08) accept both
# directions. The file expected only « entree », but its own process writes a T01 « sortie » at the traveller's
# arrival, when the commission leaves the host's money for Kwa-Ba's (prompt step 3, case FA-01), and on a refund.
# T05 (refund owed to the traveller) and T09 (payout made) stay « sortie » only.
from django.db import migrations

OFFRES = """
INSERT INTO finance_offre (code, libelle, vague, active) VALUES
    ('COURTE_DUREE', 'Hébergement courte durée, particulier', 1, true),
    ('HOTEL',        'Hébergement courte durée, hôtel',       1, true),
    ('TRANSFERT',    'Transfert aéroport',                    1, true),
    ('VOITURE_CH',   'Voiture avec chauffeur',                1, true),
    ('STRUCTURE',    'Structure, hors offre',                 1, true),
    ('VOITURE_SANS', 'Voiture sans chauffeur',                3, false),
    ('LONGUE_DUREE', 'Location longue durée',                 2, false),
    ('LOYERS',       'Encaissement des loyers et Loyer Sécurisé', 3, false),
    ('PRO',          'Kwa-Ba Pro, locaux professionnels',     3, false),
    ('EXCURSIONS',   'Excursions',                            3, false),
    ('EVASION',      'Evasion bord de mer, experiences',      1, true),
    ('EVENTS',       'Billetterie Kwa-Ba Events',             4, false)
"""

FAMILLES = """
INSERT INTO finance_famille (code, libelle, ordre) VALUES
    ('R', 'Recette : produit de Kwa-Ba',            1),
    ('D', 'Dépense : charge de Kwa-Ba',             2),
    ('T', 'Fonds de tiers : argent des partenaires',3),
    ('C', 'Caution : argent des voyageurs',         4),
    ('G', 'Fonds de garantie',                      5),
    ('F', 'Financement : capital, avances',         6),
    ('I', 'Impôts et taxes',                        7),
    ('V', 'Virement interne',                       8)
"""

NATURES = """
INSERT INTO finance_nature (code, famille, libelle, compte_syscohada, sens_attendu, actif, commentaire) VALUES
    ('R01', 'R', 'Frais de service voyageur',                    '7061', 'entree', true,  NULL),
    ('R02', 'R', 'Commission hôte particulier',                  '7062', 'entree', true,  NULL),
    ('R03', 'R', 'Commission hôtel ou résidence',                '7063', 'entree', true,  NULL),
    ('R04', 'R', 'Commission transfert aéroport',                '7064', 'entree', true,  NULL),
    ('R05', 'R', 'Commission véhicule et part sur le chauffeur', '7065', 'entree', true,  NULL),
    ('R06', 'R', 'Forfaits facultatifs (photos, accueil, clés)', '7066', 'entree', false, 'À activer'),
    ('R07', 'R', 'Forfait de garantie renforcée',                '7067', 'entree', false, 'À CONFIRMER : produit de Kwa-Ba ou fonds de tiers de l''hôte (décision associés)'),
    ('R08', 'R', 'Somme conservée après annulation',             '7068', 'entree', true,  NULL),
    ('R10', 'R', 'Honoraires longue durée, Pass Visite, états des lieux', '7071', 'entree', false, 'Vague 2'),
    ('R11', 'R', 'Encaissement des loyers et Loyer Sécurisé',    '7072', 'entree', false, 'Vague 3'),
    ('R12', 'R', 'Kwa-Ba Pro : honoraires et abonnements',       '7073', 'entree', false, 'Vague 3'),
    ('R13', 'R', 'Commission excursions',                        '7074', 'entree', false, 'Vague 3'),
    ('R14', 'R', 'Billetterie et services aux organisateurs',    '7075', 'entree', false, 'Fin 2027'),
    ('R15', 'R', 'Commission sur prestation (expérience, activité)', '7076', 'entree', true, 'Évasion, vague 2'),
    ('R16', 'R', 'Remise commerciale accordée sur un pack',      '709',  'sortie', true, 'Évasion : réduit la recette'),
    ('R17', 'R', 'Part Kwa-Ba sur les états des lieux',       '7077', 'entree', false, 'Longue durée, vague 2'),
    ('R18', 'R', 'Pénalités refacturées (carburant, retard)',  '7078', 'entree', false, 'Voiture sans chauffeur, vague 3'),
    ('D01', 'D', 'Frais de paiement du prestataire',             '6317', 'sortie', true,  'Compte 6317 : frais sur instruments de monnaie electronique. Une ligne par transaction'),
    ('D02', 'D', 'Part des apporteurs, démarcheurs et relais',   '632',  'sortie', true,  NULL),
    ('D03', 'D', 'Publicité en ligne',                           '627',  'sortie', true,  NULL),
    ('D04', 'D', 'Litige pris en charge par la Garantie Kwa-Ba', '659',  'sortie', true,  NULL),
    ('D06', 'D', 'Primes du réseau (parrainage, signalement)','632',  'sortie', true,  NULL),
    ('D10', 'D', 'Hébergement, domaine, messagerie, assistant IA','634', 'sortie', true,  NULL),
    ('D11', 'D', 'Messages WhatsApp et SMS',                     '628',  'sortie', true,  NULL),
    ('D12', 'D', 'Déplacements de terrain',                      '618',  'sortie', true,  NULL),
    ('D13', 'D', 'Frais bancaires',                              '631',  'sortie', true,  NULL),
    ('D14', 'D', 'Assurance responsabilité civile',              '625',  'sortie', true,  NULL),
    ('D15', 'D', 'Comptabilité, juriste, notaire',               '632',  'sortie', true,  NULL),
    ('D16', 'D', 'Formalités : CFE, IPDCP, enregistrement, marque','646', 'sortie', true,  NULL),
    ('D17', 'D', 'Impressions et kit des hôtes',                 '605',  'sortie', true,  NULL),
    ('D20', 'D', 'Amortissement de la Solution',                 '681',  'sortie', true,  'Écriture d''inventaire'),
    ('D21', 'D', 'Impôt sur les sociétés et minimum forfaitaire','891',  'sortie', true,  NULL),
    ('T01', 'T', 'Prix des nuits dû à l''hôte',                  '47121',NULL,     true,  NULL),
    ('T02', 'T', 'Frais de ménage dus à l''hôte',                '47121',NULL,     true,  'Reversés en totalité, jamais du chiffre d''affaires'),
    ('T03', 'T', 'Part due au propriétaire du véhicule',         '47123',NULL,     true,  NULL),
    ('T04', 'T', 'Part due au chauffeur',                        '47124',NULL,     true,  NULL),
    ('T05', 'T', 'Remboursement dû au voyageur',                 '47125','sortie', true,  NULL),
    ('T06', 'T', 'Part due au prestataire d''une prestation',   '47126',NULL,     true, 'Évasion, vague 2'),
    ('T07', 'T', 'Part due à l''organisateur d''évènements',    '47127',NULL,     false, 'Events, fin 2027'),
    ('T08', 'T', 'Pass Visite encaissé, remboursable',        '47128',NULL,     false, 'Remboursé à la signature'),
    ('T09', 'T', 'Versement effectué à un partenaire',           '47120','sortie', true,  'Solde le fonds de tiers correspondant'),
    ('C01', 'C', 'Caution reçue du voyageur',                    '165',  'entree', true,  NULL),
    ('C02', 'C', 'Caution restituée au voyageur',                '165',  'sortie', true,  NULL),
    ('C03', 'C', 'Caution retenue pour dommage',                 '165',  'sortie', true,  'Exige la référence de la décision motivée'),
    ('G01', 'G', 'Dotation au fonds de garantie',                NULL,   'sortie', true,  'À CONFIRMER : 5 % (résolution 6) ou 7 % (plan de financement) ; assiette à préciser'),
    ('G02', 'G', 'Utilisation du fonds de garantie',             NULL,   'entree', true,  NULL),
    ('F01', 'F', 'Capital libéré',                               '101',  'entree', true,  'À CONFIRMER : 500 000 ou 100 000 F CFA'),
    ('F02', 'F', 'Avance d''associé en compte courant',          '462',  'entree', true,  NULL),
    ('F03', 'F', 'Frais avancé par un associé',                  '462',  'entree', true,  NULL),
    ('F04', 'F', 'Remboursement à un associé',                   '462',  'sortie', true,  NULL),
    ('I01', 'I', 'TVA collectée',                                '4431', 'entree', false, 'À CONFIRMER auprès de l''OTR : régime et seuil'),
    ('I02', 'I', 'TVA déductible',                               '4451', 'sortie', false, 'Idem'),
    ('I03', 'I', 'Retenue à la source',                          '447',  'sortie', false, 'À CONFIRMER auprès de l''OTR'),
    ('V01', 'V', 'Virement entre comptes d''argent',             '585',  NULL,     true,  'Toujours par paire : une sortie et une entrée de même montant')
"""

COMPTES_ARGENT = """
INSERT INTO finance_compte_argent (code, libelle, type, compte_syscohada, actif) VALUES
    ('FEDAPAY',    'Compte FedaPay',                        'prestataire_paiement', '554',  true),
    ('BANQUE_EXP', 'Compte bancaire d''exploitation',       'banque',               '5211', false),
    ('BANQUE_FT',  'Compte bancaire des fonds de tiers',    'banque_fonds_tiers',   '5212', false),
    ('SECOURS',    'Prestataire de secours (sans fonds)',   'prestataire_paiement', '558',  false)
"""

MOYENS_PAIEMENT = """
INSERT INTO finance_moyen_paiement (code, libelle, taux_frais_affiche) VALUES
    ('MOOV',    'Moov Money (Flooz)',    0.0250),
    ('MIXX',    'Mixx by Yas (T-Money)', 0.0350),
    ('CARTE',   'Carte Visa ou Mastercard', 0.0360),
    ('VIREMENT','Virement bancaire',     NULL),
    ('INTERNE', 'Mouvement interne',     NULL)
"""

TIERS_TYPES = """
INSERT INTO finance_tiers_type (code, libelle, compte_syscohada, actif) VALUES
    ('voyageur',     'Voyageur',                                   '47125', true),
    ('hote',         'Hote particulier',                           '47121', true),
    ('hotel',        'Hotel ou residence',                         '47121', true),
    ('proprietaire', 'Proprietaire de vehicule',                   '47123', true),
    ('chauffeur',    'Chauffeur',                                  '47124', true),
    ('apporteur',    'Apporteur, demarcheur ou relais',            NULL, true),
    ('fournisseur',  'Fournisseur',                                NULL, true),
    ('associe',      'Associe',                                    NULL, true),
    ('etat',         'Etat et organismes',                         NULL, true),
    ('interne',      'Mouvement interne',                          NULL, true),
    ('prestataire',  'Prestataire d''une prestation (Evasion)',    '47126', true),
    ('organisateur', 'Organisateur d''evenements',                 '47127', false),
    ('bailleur',     'Bailleur longue duree ou Kwa-Ba Pro',        '47128', false)
"""

PARAMETRES = """
INSERT INTO finance_parametre (cle, valeur, unite, categorie, offre_code, libelle, source, actif) VALUES
('frais_service_voyageur',        6, 'pourcentage','tarif','COURTE_DUREE','Frais de service voyageur','Grille 2.3',true),
('frais_service_reduit',          3, 'pourcentage','tarif','COURTE_DUREE','Frais reduits : Client fidele, Pack Sejour','Grille 2.3',true),
('frais_service_entreprise',      4, 'pourcentage','tarif','COURTE_DUREE','Frais voyageur, contrat cadre entreprise','Grille 2.3',true),
('commission_hote',               8, 'pourcentage','tarif','COURTE_DUREE','Commission hote particulier','Grille 2.3',true),
('commission_hote_fondateur',     5, 'pourcentage','tarif','COURTE_DUREE','Commission des 50 hotes fondateurs, 6 mois','Grille 2.3',true),
('commission_hotel',             12, 'pourcentage','tarif','HOTEL','Commission hotel ou residence','Grille 2.3',true),
('menage_chambre_privee',      3000, 'fcfa','forfait','COURTE_DUREE','Frais de menage, chambre privee','Decision 31 oct.',true),
('menage_studio',              5000, 'fcfa','forfait','COURTE_DUREE','Frais de menage, studio','Decision 31 oct.',true),
('menage_appartement_t2',      7500, 'fcfa','forfait','COURTE_DUREE','Frais de menage, appartement T2','Decision 31 oct.',true),
('menage_appartement_t3',     10000, 'fcfa','forfait','COURTE_DUREE','Frais de menage, appartement T3 et plus','Decision 31 oct.',true),
('menage_villa',              15000, 'fcfa','forfait','COURTE_DUREE','Frais de menage, villa ou maison entiere','Decision 31 oct.',true),
('commission_vehicule',          15, 'pourcentage','tarif','VOITURE_CH','Commission du proprietaire de vehicule','Offre mobilite 3.2',true),
('commission_vehicule_fidele',   12, 'pourcentage','tarif','VOITURE_CH','Proprietaire Fidele, apres 20 locations','Offre mobilite 3.2',true),
('commission_vehicule_fondateur',10, 'pourcentage','tarif','VOITURE_CH','20 premiers proprietaires, 6 mois','Offre mobilite 3.2',true),
('chauffeur_prix_jour',        7000, 'fcfa','tarif','VOITURE_CH','Prix du chauffeur par jour, paye par le client','Offre mobilite 3.2',true),
('chauffeur_part_jour',        6000, 'fcfa','tarif','VOITURE_CH','Part du chauffeur par jour','Offre mobilite 3.2',true),
('chauffeur_part_excellence',  6500, 'fcfa','tarif','VOITURE_CH','Part du chauffeur Excellence ou Mon chauffeur','Offre mobilite 3.2',true),
('chauffeur_prime_pays',       1500, 'fcfa','forfait','VOITURE_CH','Prime de deplacement dans le pays, au chauffeur','Offre mobilite 3.2',true),
('chauffeur_prime_hors_pays',  2000, 'fcfa','forfait','VOITURE_CH','Prime de deplacement hors du pays, au chauffeur','Offre mobilite 3.2',true),
('transfert_part_chauffeur',   3000, 'fcfa','tarif','TRANSFERT','Part du chauffeur partenaire, Grand Lome (a valider)','Offre mobilite 3.3',true),
('caution_vehicule_plafond', 100000, 'fcfa','plafond','VOITURE_SANS','Plafond de la caution vehicule','Offre mobilite 6',false),
('caution_vehicule_jours',        2, 'jours','plafond','VOITURE_SANS','Caution standard, en journees de location','Offre mobilite 6',false),
('penalite_carburant',         2000, 'fcfa','forfait','VOITURE_SANS','Supplement carburant manquant','CGV art. 14.4',false),
('penalite_retard_horaire',      10, 'pourcentage','tarif','VOITURE_SANS','Retard par heure au-dela de 30 min','CGV art. 14.5',false),
('apporteur_part',               20, 'pourcentage','tarif',NULL,'Part de l''apporteur sur le revenu Kwa-Ba','Charte art. 4',true),
('apporteur_duree_mois',         12, 'mois','delai',NULL,'Duree de la part d''apporteur','Charte art. 4',true),
('demarcheur_part',              60, 'pourcentage','tarif','LONGUE_DUREE','Part du demarcheur sur les honoraires','Charte art. 4',false),
('demarcheur_part_confirme',     65, 'pourcentage','tarif','LONGUE_DUREE','Part du demarcheur Confirme','Charte art. 5',false),
('forfait_photos',             5000, 'fcfa','forfait','COURTE_DUREE','Forfait photos d''annonce','Charte art. 4',true),
('forfait_photos_relais',      3500, 'fcfa','forfait','COURTE_DUREE','Part du relais sur les photos','Charte art. 4',true),
('forfait_accueil',            3000, 'fcfa','forfait','COURTE_DUREE','Forfait accueil du voyageur','Charte art. 4',true),
('forfait_accueil_relais',     2000, 'fcfa','forfait','COURTE_DUREE','Part du relais sur l''accueil','Charte art. 4',true),
('forfait_remise_cles',        3000, 'fcfa','forfait','VOITURE_SANS','Forfait remise des cles','Charte art. 4',false),
('prime_parrainage',           5000, 'fcfa','forfait',NULL,'Prime de parrainage d''un partenaire','Charte art. 4',true),
('prime_signalement',          5000, 'fcfa','forfait',NULL,'Prime pour un signalement verifie','Charte art. 10',true),
('prime_point_etape',          3000, 'fcfa','forfait','LOYERS','Prime du relais, point d''etape Loyer Securise','Loyer Securise 9.1',false),
('prime_verification',            0, 'fcfa','forfait',NULL,'A FIXER par les associes : prime de premiere verification','Charte art. 4',true),
('direct_hote',                   5, 'pourcentage','tarif','COURTE_DUREE','Lien Kwa-Ba Direct, hote','Grille 2.3',false),
('direct_hotel',                  6, 'pourcentage','tarif','HOTEL','Lien Kwa-Ba Direct, hotel','Grille 2.3',false),
('direct_vehicule',               8, 'pourcentage','tarif','VOITURE_CH','Lien Kwa-Ba Direct, proprietaire','Grille 2.3',false),
('direct_chauffeur',            500, 'fcfa','tarif','VOITURE_CH','Lien Kwa-Ba Direct, chauffeur par jour','Grille 2.3',false),
('honoraires_mois',               1, 'mois','tarif','LONGUE_DUREE','Honoraires de mise en relation, partages a parts egales','Offre longue duree 4',false),
('pass_visite',                2000, 'fcfa','tarif','LONGUE_DUREE','Pass Visite, rembourse a la signature','Offre longue duree 4',false),
('pass_visite_demarcheur',     1500, 'fcfa','forfait','LONGUE_DUREE','Part du demarcheur par visite confirmee','Offre longue duree 4',false),
('pass_visite_max',               3, 'code','plafond','LONGUE_DUREE','Nombre de visites remboursees a la signature','Offre longue duree 4',false),
('edl_chambre',                4000, 'fcfa','forfait','LONGUE_DUREE','Etat des lieux, chambre ou studio','Loyer Securise 9.2',false),
('edl_appartement',           10000, 'fcfa','forfait','LONGUE_DUREE','Etat des lieux, appartement','Loyer Securise 9.2',false),
('edl_villa',                 16000, 'fcfa','forfait','LONGUE_DUREE','Etat des lieux, villa','Loyer Securise 9.2',false),
('edl_part_relais',              60, 'pourcentage','tarif','LONGUE_DUREE','Part du relais sur l''etat des lieux','Loyer Securise 9.2',false),
('loyers_encaissement',           5, 'pourcentage','tarif','LOYERS','Encaissement simple des loyers','Loyer Securise 9.1',false),
('loyer_securise',                6, 'pourcentage','tarif','LOYERS','Loyer Securise, paye par le proprietaire','Loyer Securise 9.1',false),
('loyer_securise_pilote',         5, 'pourcentage','tarif','LOYERS','Pilote : 20 proprietaires, 6 mois','Loyer Securise 9.1',false),
('pro_essentielle_min',       50000, 'fcfa','tarif','PRO','Formule Essentielle, minimum','Kwa-Ba Pro',false),
('pro_visibilite_mois',       15000, 'fcfa','tarif','PRO','Visibilite, par annonce et par mois','Kwa-Ba Pro',false),
('pro_abonnement_mois',       50000, 'fcfa','tarif','PRO','Abonnement Pro mensuel','Kwa-Ba Pro',false),
('pro_recherche',             50000, 'fcfa','tarif','PRO','Recherche sur mesure, deduite a la signature','Kwa-Ba Pro',false),
('pro_espaces',                  12, 'pourcentage','tarif','PRO','Espaces a la demande','Kwa-Ba Pro',false),
('events_commission',             8, 'pourcentage','tarif','EVENTS','Commission de billetterie, tout compris','Events 4',false),
('events_commission_fidele',      7, 'pourcentage','tarif','EVENTS','A partir du 4e evenement sans incident','Events 4',false),
('events_minimum_billet',       150, 'fcfa','plafond','EVENTS','Minimum par billet payant','Events 4',false),
('events_gratuit_seuil',        300, 'code','seuil','EVENTS','Billets gratuits sans frais','Events 4',false),
('events_gratuit_unitaire',     100, 'fcfa','tarif','EVENTS','Au-dela du seuil, par billet gratuit','Events 4',false),
('events_controle_acces',     25000, 'fcfa','forfait','EVENTS','Controle d''acces, par evenement','Events 4',false),
('events_controleur',          5000, 'fcfa','forfait','EVENTS','Par controleur et par vacation','Events 4',false),
('events_controleur_relais',   3500, 'fcfa','forfait','EVENTS','Part du relais par vacation','Events 4',false),
('events_mise_en_avant',      25000, 'fcfa','forfait','EVENTS','Mise en avant, par evenement','Events 4',false),
('events_versement_jours',        3, 'jours','delai','EVENTS','Versement a l''organisateur apres l''evenement','Events 4',false),
('events_force_majeure',        3.5, 'pourcentage','tarif','EVENTS','Retenue en cas de force majeure','Events 10',false),
('excursions_commission',        15, 'pourcentage','tarif','EXCURSIONS','A DECIDER : resolution 19 non votee','Grille 2.3',false),
('caution_plafond_fcfa',     150000, 'fcfa','plafond','COURTE_DUREE','Plafond de la caution sequestree','Decisions 29 oct.',true),
('caution_plafond_nuits',         2, 'nuits','plafond','COURTE_DUREE','Plafond de la caution en nuits','Decisions 29 oct.',true),
('caution_restitution_heures',   72, 'heures','delai','COURTE_DUREE','Delai de restitution apres le depart','Decisions 29 oct.',true),
('garantie_renforcee_multiple',   5, 'code','plafond','COURTE_DUREE','Plafond de couverture = N fois le forfait','Decisions 29 oct.',true),
('versement_hote_heures',        24, 'heures','delai',NULL,'Versement a l''hote apres l''arrivee','CGV art. 8',true),
('versement_reseau_heures',      48, 'heures','delai',NULL,'Versement au reseau','Charte art. 6',true),
('groupage_seuil_fcfa',        5000, 'fcfa','seuil',NULL,'Sous ce montant, versement groupe le vendredi','Charte art. 6',true),
('prestataire_solde_alerte',4000000, 'fcfa','seuil',NULL,'Alerte sur le solde chez le prestataire','Plan de secours',true),
('prestataire_solde_plafond',5000000,'fcfa','plafond',NULL,'Plafond du solde chez le prestataire','Plan de secours',true),
('publicite_par_reservation',  3100, 'fcfa','plafond','STRUCTURE','Plafond de publicite par reservation','Resolution 17',true),
('frais_associe_plafond_mois',50000, 'fcfa','plafond','STRUCTURE','Plafond mensuel des frais par associe','Pacte art. 3.3',true),
('charges_fixes_mois',       151500, 'fcfa','seuil','STRUCTURE','Charges fixes mensuelles 2027, pour le point mort','Plan de financement',true),
('impot_societes',               27, 'pourcentage','tarif','STRUCTURE','Impot sur les societes','Plan de financement',true),
('impot_minimum',                 1, 'pourcentage','tarif','STRUCTURE','Minimum forfaitaire sur le chiffre d''affaires','Plan de financement',true),
('tva_taux',                     18, 'pourcentage','tarif','STRUCTURE','TVA, si elle s''applique','A CONFIRMER aupres de l''OTR',false),
('tva_seuil',             100000000, 'fcfa','seuil','STRUCTURE','Seuil d''assujettissement a la TVA','100 M confirme par deux sources publiques 2026 ; a faire confirmer par ecrit aupres de l''OTR',false),
('duree_conservation_annees',    10, 'code','delai','STRUCTURE','Duree de conservation des livres et pieces, en annees','AUDCIF',true),
('facture_serie_annuelle',        1, 'code','interne','STRUCTURE','Numerotation des factures : une serie continue par annee civile, sans trou','LPF Togo art. 64',true),
('caution_evasion_plafond',       0, 'fcfa','plafond','EVASION','A FIXER : plafond de caution releve pour les villas bord de mer','Evasion EVA-02',true),
('caution_evasion_nuits',         0, 'nuits','plafond','EVASION','A FIXER : plafond de caution Evasion, en nuits','Evasion EVA-02',true),
('experience_commission',         0, 'pourcentage','tarif','EVASION','A FIXER : commission Kwa-Ba sur une Experience','Evasion EVA-08',true),
('experience_apporteur_hote',     0, 'pourcentage','tarif','EVASION','A FIXER : part d''apporteur de l''hote sur une Experience (posture B)','Evasion EVA-05',true),
('pack_remise_max',               0, 'pourcentage','plafond','EVASION','A FIXER : remise maximale sur un pack','Evasion EVA-10',true),
('fonds_garantie_taux',           0, 'pourcentage','tarif','STRUCTURE','A TRANCHER : 5 % (resolution 6) ou 7 % (plan de financement)','Ecart de referentiel',true),
('double_validation_seuil',       0, 'fcfa','seuil','STRUCTURE','A FIXER : seuil de double validation des versements','Reunion',true),
('garantie_renforcee_beneficiaire',0,'code','interne','COURTE_DUREE','A TRANCHER : 0 non decide, 1 Kwa-Ba, 2 hote','Reunion',true)
"""

AXES = """
INSERT INTO finance_axe (code, libelle, colonne) VALUES
    ('mois',      'Mois comptable',       'mois'),
    ('annee',     'Année',                'annee'),
    ('famille',   'Famille de nature',    'famille'),
    ('nature',    'Nature',               'nature_code'),
    ('offre',     'Offre',                'offre_code'),
    ('tiers',     'Type de tiers',        'tiers_type'),
    ('moyen',     'Moyen de paiement',    'moyen_paiement_code'),
    ('compte',    'Compte d''argent',     'compte_argent_code'),
    ('prestation','Type de prestation',   'prestation_type'),
    ('compte_cpt','Compte comptable',     'compte_syscohada')
"""

RAPPORTS = """
INSERT INTO finance_rapport (code, titre, axe1, axe2, familles, periodicite, destinataire) VALUES
    ('recettes_type',   'Recettes par type et par offre',      'nature', 'offre', ARRAY['R'],      'mensuel',    'associes'),
    ('depenses_type',   'Dépenses par type',                   'nature', 'mois',  ARRAY['D'],      'mensuel',    'associes'),
    ('marge_offre',     'Marge par offre',                     'offre',  'mois',  ARRAY['R','D'],  'mensuel',    'associes'),
    ('du_partenaires',  'Sommes dues par partenaire',          'tiers',  NULL,    ARRAY['T'],      'quotidien',  'dirigeants'),
    ('cautions',        'Cautions détenues',                   'mois',   NULL,    ARRAY['C'],      'quotidien',  'dirigeants'),
    ('tresorerie',      'Mouvements par compte d''argent',     'compte', 'mois',  NULL,            'mensuel',    'dirigeants'),
    ('frais_paiement',  'Frais de paiement par moyen',         'moyen',  'mois',  ARRAY['D'],      'mensuel',    'dirigeants'),
    ('comptes_assoc',   'Comptes courants d''associés',        'tiers',  'mois',  ARRAY['F'],      'mensuel',    'associes'),
    ('balance',         'Balance par compte comptable',        'compte_cpt','mois',NULL,           'mensuel',    'cabinet')
"""

# Reverse: children first
TABLES = ['finance_rapport', 'finance_axe', 'finance_parametre', 'finance_tiers_type', 'finance_moyen_paiement',
          'finance_compte_argent', 'finance_nature', 'finance_famille', 'finance_offre']


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            [OFFRES, FAMILLES, NATURES, COMPTES_ARGENT, MOYENS_PAIEMENT, TIERS_TYPES, PARAMETRES, AXES, RAPPORTS],
            [f'DELETE FROM {table}' for table in TABLES],
        ),
    ]
