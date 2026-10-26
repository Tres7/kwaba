"""Contract templates, installed by the migration then editable in the back-office.

Drafts (contracts B1, B2, B4, B5 and B6, charter of the Kwa-Ba Partners Network B14, version 1 of
18 October 2026): to be reviewed by a lawyer before the first signature.
Available variables: see services.VARIABLES.
"""

PREAMBULE = """Entre les soussignés :

{{ societe.raison_sociale }}, {{ societe.forme_juridique }}, dont le siège est situé {{ societe.adresse }}, {{ societe.pays }}, immatriculée au RCCM sous le numéro {{ societe.rccm }}, NIF {{ societe.nif }}, exploitant la plateforme Kwa-Ba ({{ societe.site }}), représentée par {{ societe.representant }}, ci-après « KWA-BA »,

et

{{ partie.nom }}, {{ partie.coordonnees }}, {{ partie.details }} ci-après « {{ partie.designation }} ».

Le présent contrat s'applique avec les conditions générales de vente (CGV) et les conditions générales d'utilisation (CGU) de la plateforme Kwa-Ba (la « Plateforme »), et avec la charte du Réseau Kwa-Ba Partenaires reproduite en annexe, qui en fait partie intégrante."""

COMMUN_FIN = """## Données personnelles
Chaque partie traite les données personnelles reçues de l'autre, et celles des clients, uniquement pour l'exécution du présent contrat, conformément à la loi n° 2019-014 du 29 octobre 2019 relative à la protection des données à caractère personnel. Elle les garde confidentielles et ne les communique à aucun tiers non autorisé. Les données des clients ne peuvent être utilisées à des fins commerciales en dehors de la Plateforme.

## Durée et résiliation
Le présent contrat prend effet à la date de sa signature, pour une durée indéterminée. Chaque partie peut y mettre fin par écrit (courriel ou messagerie Kwa-Ba), moyennant un préavis de trente (30) jours ; les engagements en cours à la date de fin restent exécutés. En cas de faute grave (fraude, mise en danger d'un client, faux document, violence, vol), KWA-BA peut suspendre ou résilier le contrat sans préavis.

## Signature électronique et preuve
Les parties signent le présent contrat par voie électronique. La signature est apposée au moyen d'un lien personnel adressé par courriel ou depuis le compte Kwa-Ba du signataire ; l'horodatage, l'adresse IP, le navigateur utilisé et l'empreinte numérique (SHA-256) du document sont conservés et figurent sur le certificat de signature annexé. Conformément à la loi n° 2017-07 relative aux transactions électroniques, l'écrit électronique a la même force probante que l'écrit papier.

## Droit applicable et litiges
Le présent contrat est soumis au droit togolais et aux actes uniformes de l'OHADA. Les parties cherchent d'abord un accord amiable pendant trente (30) jours, avec l'aide d'un associé de KWA-BA désigné comme médiateur. À défaut, le tribunal de commerce de Lomé est compétent."""


CHARTE = """## Annexe – Charte du Réseau Kwa-Ba Partenaires
La présente charte fixe les règles communes à tous les partenaires : ce que Kwa-Ba leur apporte, ce qu'ils gagnent et les engagements de chacun. Son principe est simple : Kwa-Ba s'ajoute à l'activité du partenaire, elle ne la remplace pas. En contrepartie, tout client rencontré grâce à Kwa-Ba reste un client Kwa-Ba.

## Charte, article 1 – Qui est concerné
Démarcheur (longue durée et Kwa-Ba Pro) : apporte des logements ou des locaux à louer et organise les visites.
Apporteur (courte durée, mobilité, événements) : fait inscrire des hôtes, des véhicules, des chauffeurs ou des organisateurs d'événements.
Relais de terrain : visites, états des lieux, accueil des voyageurs, remise des clés, photos d'annonce, premières vérifications, contrôle d'accès aux événements.
Hôte, hôtel, propriétaire de véhicule, chauffeur, bailleur, organisateur d'événements : fournit la prestation réservée ; la charte complète son contrat propre.
Une même personne peut exercer plusieurs rôles.

## Charte, article 2 – Statut du partenaire
Le partenaire est indépendant. Il n'existe aucun lien de subordination, aucun contrat de travail et aucun salaire entre lui et KWA-BA. Il organise librement son temps et ses moyens et reste responsable de ses propres obligations fiscales, sociales et administratives. Il n'est pas autorisé à engager KWA-BA, à signer en son nom ni à encaisser des sommes pour elle.

## Charte, article 3 – Adhésion
Conditions : être majeur ; présenter une pièce d'identité valide ; fournir un casier judiciaire ou une attestation équivalente pour les chauffeurs et les relais qui entrent chez des clients ; suivre la formation d'accueil de KWA-BA ; signer la présente charte et, le cas échéant, le contrat propre à son activité. Le partenaire reçoit une carte « Partenaire Kwa-Ba » nominative, qui permet aux clients de vérifier son statut, et un profil sur la Plateforme. La carte reste la propriété de KWA-BA et lui est rendue en fin de partenariat.

## Charte, article 4 – Missions et rémunérations
– Courte durée, hôte apporté : 20 % du revenu de KWA-BA (frais voyageur et commission) sur les réservations de cet hôte, pendant 12 mois à compter de sa première réservation.
– Mobilité, véhicule ou chauffeur apporté : 20 % du revenu de KWA-BA sur ses locations ou missions, pendant 12 mois à compter de la première.
– Photos d'une annonce (payées par l'hôte) : 3 500 F CFA sur un forfait de 5 000.
– Accueil des voyageurs (payé par l'hôte) : 2 000 F CFA sur un forfait de 3 000.
– Remise des clés d'un véhicule sans chauffeur (payée par le propriétaire, dès l'ouverture de ce service) : 2 000 F CFA sur un forfait de 3 000.
– Première vérification d'un logement, d'un véhicule ou d'un chauffeur : prime par dossier fixée par les associés.
– Parrainage d'un nouveau partenaire : 5 000 F CFA après sa première mission rémunérée.
Les rémunérations de la longue durée, de Kwa-Ba Pro et de Kwa-Ba Events s'appliqueront à l'ouverture de ces services. Le partenaire ne perçoit aucune autre somme des clients pour les opérations faites par Kwa-Ba : ni droit de visite, ni commission, ni pourboire exigé.

## Charte, article 5 – Niveaux et avantages
– Chauffeur Excellence : 20 missions, note d'au moins 4,7, aucun retard de plus de 15 minutes ni plainte fondée sur 3 mois ; 6 500 F CFA par jour au lieu de 6 000, priorité Pack Séjour et entreprises, badge.
– Mon chauffeur : mission redemandée par un client ; 6 500 F CFA par jour sur cette mission.
– Propriétaire Fidèle (véhicules) : 20 locations sans incident ; commission de 12 % au lieu de 15 %.
– Fondateurs : 50 premiers hôtes, 20 premiers propriétaires de véhicules, 10 premiers chauffeurs ; avantages du Programme Fondateurs pendant 6 mois.
Les niveaux sont revus chaque trimestre. Un incident grave fait perdre le niveau.

## Charte, article 6 – Paiement des partenaires
Les sommes dues sont versées par Mobile Money, sur un compte au nom du partenaire, sous 48 heures après le fait qui les déclenche (mission terminée, réservation consommée), sauf délai plus court prévu au contrat propre du partenaire. Les sommes de moins de 5 000 F CFA peuvent être cumulées et versées en une fois chaque vendredi, pour limiter les frais de versement. Un relevé mensuel détaille toutes les sommes versées. Toute réclamation sur un paiement est traitée sous 72 heures. Si le prestataire de paiement est indisponible, bloque les fonds ou fait défaut, les délais de versement sont suspendus pendant l'incident ; KWA-BA en informe le partenaire sans délai et verse les sommes dues dès que possible, au besoin par un autre prestataire agréé ou par virement. Elle ne répond pas d'un retard dû uniquement à cette défaillance, sauf faute de sa part.

## Charte, article 7 – Non-exclusivité
Le partenaire reste libre de travailler pour son propre compte et avec d'autres acteurs, sauf pour les clients, les biens et les opérations venus de Kwa-Ba (article 9). Une annonce publiée sur Kwa-Ba respecte les tarifs de Kwa-Ba pour les clients de la Plateforme.

## Charte, article 8 – Engagements du partenaire
Le partenaire s'engage à :
1. publier des annonces exactes : photos réelles, prix complet, sommes demandées à l'entrée ;
2. respecter la loi, notamment les règles de sécurité et d'assurance pour les véhicules ;
3. ne jamais encaisser d'argent en dehors de la Plateforme pour une opération venue de Kwa-Ba ; seul fait exception, pour l'hôte concerné, le dépôt de garantie d'un logement remis contre reçu ;
4. traiter les clients avec respect, sans discrimination, et être ponctuel ;
5. utiliser la Plateforme pour les réservations, les messages, les photos et les états des lieux ;
6. protéger les données des clients et ne les utiliser que pour la mission (loi n° 2019-014) ;
7. signaler à KWA-BA tout incident, toute fraude ou toute tentative de contournement ;
8. utiliser le nom, le logo et la carte Kwa-Ba seulement dans le cadre de ses missions.

## Charte, article 9 – Non-contournement et non-sollicitation
Est un client Kwa-Ba toute personne présentée par la Plateforme, ou qui a réservé, visité ou loué par elle ; les messages et les réservations en font la preuve. Pendant 12 mois après le dernier contact par Kwa-Ba, le partenaire s'interdit de proposer à un client Kwa-Ba de réserver, louer ou payer en dehors de la Plateforme, et d'accepter une telle proposition venant du client. Le partenaire qui souhaite servir ses propres clients par la Plateforme peut utiliser le Lien Kwa-Ba Direct, à tarif réduit, dès son ouverture : 5 % pour un hôte, 6 % pour un hôtel, 8 % pour un propriétaire de véhicule, 500 F CFA par jour pour un chauffeur.

## Charte, article 10 – Contrôles et signalements
KWA-BA peut faire des contrôles : appels aux clients après une prestation, vérification des annonces retirées, visites mystères. Tout signalement vérifié d'un contournement est récompensé par 5 000 F CFA. L'identité de l'auteur du signalement reste confidentielle.

## Charte, article 11 – Sanctions
– Premier manquement à l'article 8 ou 9 : avertissement écrit et perte de la rémunération liée à l'opération.
– Récidive : suspension d'un mois.
– Troisième manquement, fraude ou faute grave (violence, vol, faux document) : exclusion du réseau, retrait de la carte et réclamation des sommes perdues par KWA-BA.
Avant toute sanction, le partenaire est informé par écrit des faits reprochés et dispose de 7 jours pour s'expliquer. KWA-BA ne publie jamais le nom d'un partenaire sanctionné.

## Charte, article 12 – Durée et fin du partenariat
La charte est conclue pour une durée indéterminée. Chaque partie peut y mettre fin par écrit avec un préavis de 30 jours, ou sans préavis en cas de faute grave. Les sommes acquises avant la fin du partenariat sont versées. Les parts de 20 % sur 12 mois restent dues jusqu'à leur terme, sauf exclusion pour faute. L'obligation de non-contournement continue de s'appliquer pendant 12 mois.

## Charte, article 13 – Modification
KWA-BA peut modifier la charte et les rémunérations. Le partenaire en est informé au moins 30 jours à l'avance. Il peut mettre fin au partenariat s'il refuse la modification."""


HOTE = PREAMBULE + """

## Article 1 – Objet
L'Hôte confie à KWA-BA la publication et la commercialisation de son logement meublé pour des séjours de courte durée, dans les conditions du présent contrat. Il déclare être propriétaire du logement, mandataire du propriétaire (mandat écrit remis à KWA-BA) ou locataire autorisé à sous-louer (accord écrit remis à KWA-BA).

## Article 2 – Commission et versements
– Commission de KWA-BA : 8 % du prix des nuits (hors frais de service payés par le client).
– Programme Fondateurs (50 premiers hôtes) : 5 % pendant 6 mois ; {{ partie.fondateur }}.
– Lien Kwa-Ba Direct (propres clients de l'Hôte, dès son ouverture) : 5 %, sans frais de service pour le client.
– Frais de service du client (6 %, 3 % en Pack Séjour ou en Client fidèle, 4 % entreprises) : payés par le client, ils ne réduisent pas le revenu de l'Hôte.
– Versement : 24 heures après l'arrivée du client, par Mobile Money, commission déduite, sur le compte au nom de l'Hôte indiqué dans son espace hôte.
– Forfaits facultatifs commandés par l'Hôte : photos de l'annonce, 5 000 F CFA ; accueil des voyageurs, 3 000 F CFA par arrivée ; déduits des versements.
La part reversée au démarcheur qui a apporté l'Hôte (20 % du revenu de KWA-BA pendant 12 mois) est payée par KWA-BA et ne coûte rien à l'Hôte.

## Article 3 – Annonce
3.1. L'Hôte fixe librement son prix par nuit et ses frais de ménage éventuels.
3.2. Il choisit, pour chaque annonce, sa politique d'annulation : Souple, Modérée ou Ferme (définies dans les CGV).
3.3. Il indique ses règles : heures d'arrivée et de départ, nombre maximal de personnes, animaux, tabac, fêtes (interdites sauf autorisation), visiteurs, barème du départ tardif (dans la limite d'une nuit).
3.4. Dépôt de garantie (facultatif) : dans la limite d'une nuit et de 50 000 F CFA. Il est indiqué sur l'annonce, remis à l'arrivée contre un reçu et restitué au départ, ou au plus tard sous 48 heures. Seul le montant d'un dommage déclaré selon l'article 5 peut être conservé, jusqu'à l'avis de KWA-BA.
3.5. L'Hôte tient son calendrier à jour. Un logement réservé ailleurs doit être bloqué sur la Plateforme sans délai.

## Article 4 – Obligations de l'Hôte
L'Hôte s'engage à :
1. remettre un logement propre, sûr et conforme à l'annonce : eau, électricité, équipements annoncés, serrures en état et, si possible, extincteur ou détecteur de fumée ;
2. organiser l'arrivée (accueil ou remise des clés) à l'heure convenue, et rester joignable par la messagerie de la Plateforme pendant le séjour ;
3. régler sous 24 heures tout problème important signalé (eau, électricité, sécurité) ; à défaut, la Garantie Kwa-Ba s'applique à ses frais ;
4. demander la pièce d'identité des voyageurs si la réglementation l'impose (registre des voyageurs) ;
5. refuser l'accueil de mineurs non accompagnés d'un parent ou d'un adulte responsable muni d'une autorisation, et signaler toute situation suspecte ;
6. respecter la réglementation applicable : autorisations éventuelles, déclarations fiscales de ses revenus, taxe de séjour si elle est applicable ;
7. assurer le logement et sa responsabilité civile (fortement recommandé ; KWA-BA peut l'exiger pour les grands logements ou les villas).

## Article 5 – Dommages causés par un client
5.1. L'Hôte déclare les dommages dans les 48 heures suivant le départ, par la Plateforme, avec des photos et un devis ou une facture.
5.2. Le client dispose de 72 heures pour répondre. À défaut d'accord, KWA-BA rend un avis motivé, en tenant compte de l'usure normale.
5.3. Le montant retenu est d'abord pris sur le dépôt de garantie, puis réclamé au client. KWA-BA ne garantit pas le paiement du solde par le client.

## Article 6 – Garantie Kwa-Ba et recours
Si le client est relogé ou remboursé parce que le logement est très différent de l'annonce, insalubre, dangereux, inaccessible ou déjà occupé, ou parce qu'un problème important n'a pas été réglé, les sommes correspondantes sont à la charge de l'Hôte. Elles sont compensées sur ses versements suivants.

## Article 7 – Vérification et qualité
7.1. Avant toute publication, l'Hôte fournit une pièce d'identité en cours de validité, et un agent de KWA-BA visite le logement pour contrôler sa conformité avec l'annonce. Un logement n'est visible des clients qu'après cette vérification ; KWA-BA peut le revisiter avec un préavis de 48 heures.
7.2. Une note moyenne inférieure à 3,5 sur 5 après au moins 5 séjours entraîne un entretien et un plan d'amélioration. L'annonce peut être suspendue si la note ne s'améliore pas dans les 3 mois.

""" + COMMUN_FIN + "\n\n" + CHARTE


HOTEL = PREAMBULE + """

## Article 1 – Objet
L'Établissement confie à KWA-BA la commercialisation de ses chambres ou appartements sur la Plateforme, dans les conditions du présent contrat. Il déclare détenir la licence d'exploitation délivrée par le ministère chargé du tourisme, dont il remet copie à KWA-BA.

## Article 2 – Commission et versements
– Commission de KWA-BA : 12 % du prix de l'hébergement, hors taxe de séjour éventuelle.
– Lien Kwa-Ba Direct (réservations apportées par l'Établissement, dès son ouverture) : 6 %.
– Frais de service du client (6 %, 3 % en Pack Séjour ou en Client fidèle, 4 % entreprises) : payés par le client, ils ne réduisent pas le revenu de l'Établissement.
– Versement : 24 heures après l'arrivée du client, commission déduite, sur le compte de l'Établissement indiqué dans son espace ; relevé et facture de commission mensuels.
– Taxe de séjour ou taxe locale éventuelle : indiquée sur l'annonce, incluse dans le prix total, collectée et déclarée par l'Établissement.

## Article 3 – Tarifs, disponibilités et conditions
3.1. L'Établissement fixe librement ses tarifs et ses disponibilités, et les tient à jour. Aucune clause de prix identique sur tous les canaux ne lui est imposée.
3.2. Il choisit l'une des politiques d'annulation des CGV (Souple, Modérée ou Ferme) ou applique sa propre politique, si elle est plus favorable au client. Elle est affichée avant la réservation.
3.3. Les petits-déjeuners, taxes, suppléments et services inclus ou payants sont indiqués clairement. Aucun supplément non affiché ne peut être réclamé sur place, sauf consommation choisie par le client.

## Article 4 – Engagements de l'Établissement
L'Établissement s'engage à :
1. détenir et maintenir sa licence d'exploitation et ses assurances (responsabilité civile, incendie), et en remettre copie à KWA-BA ;
2. fournir la chambre réservée, ou une chambre de catégorie égale ou supérieure, sans supplément ;
3. en cas de surréservation, loger le client dans un établissement de catégorie égale ou supérieure, à proximité, et prendre en charge la différence de prix et le transport ;
4. tenir le registre des voyageurs exigé par la réglementation ;
5. pendant le séjour, ne pas inviter le client à annuler sa réservation pour la refaire directement (non-sollicitation), ni à payer en dehors de la Plateforme ;
6. répondre aux réclamations transmises par KWA-BA dans les 24 heures.

## Article 5 – Garantie Kwa-Ba et recours
Si le client est relogé ou remboursé parce que la chambre est très différente de l'annonce, indisponible ou insalubre, les sommes correspondantes sont à la charge de l'Établissement. Elles sont compensées sur ses versements suivants.

## Article 6 – Contrat cadre entreprises (ouverture ultérieure)
Lorsque le service Kwa-Ba Entreprises sera ouvert, l'Établissement pourra accepter des réservations groupées d'entreprises et d'ONG sous contrat cadre (frais de 4 % pour le client). Ses conditions particulières (tarifs négociés, facture mensuelle) feront l'objet d'un avenant.

""" + COMMUN_FIN + "\n\n" + CHARTE


LOUEUR = PREAMBULE + """

## Article 1 – Véhicules et documents
Les véhicules du Propriétaire sont enregistrés par KWA-BA sur la Plateforme : marque, modèle, année, immatriculation, nombre de places, titulaire de la carte grise, validité de la visite technique, assurance (compagnie, numéro, validité, usages couverts). Le Propriétaire remet une copie de ces documents avant toute publication et à chaque renouvellement. Un véhicule dont un document a expiré est retiré de la Plateforme jusqu'à sa régularisation.

## Article 2 – Formules proposées
Pour chaque véhicule, le Propriétaire choisit les formules proposées : location avec chauffeur, location sans chauffeur. La location avec chauffeur est assurée par un chauffeur partenaire de Kwa-Ba (contrat chauffeur), ou par le Propriétaire lui-même s'il signe aussi le contrat chauffeur.

## Article 3 – Commission et versements
– Commission de KWA-BA : 15 % du prix de location du véhicule, payés par le Propriétaire ; aucun frais pour le client sur le véhicule.
– Programme Fondateurs (20 premiers propriétaires) : 10 % pendant 6 mois ; {{ partie.fondateur }}.
– Propriétaire Fidèle : 12 % après 20 locations sans incident.
– Lien Kwa-Ba Direct (propres clients du Propriétaire, dès son ouverture) : 8 %.
– Prix du chauffeur : payé par le client (7 000 F CFA par jour), versé au chauffeur ; il ne revient pas au Propriétaire.
– Versement : par Mobile Money, commission déduite, 24 heures après le début de la location ; lorsque la location comporte un dépôt de garantie, à la fin du délai de signalement des dommages (article 4.2).
– Forfait facultatif de remise des clés et d'état des lieux par un relais (location sans chauffeur, dès l'ouverture de ce service) : 3 000 F CFA par remise, déduits des versements.

## Article 4 – Prix et conditions fixés par le Propriétaire
4.1. Le Propriétaire fixe librement le prix par jour, le kilométrage inclus et le prix du kilomètre supplémentaire, le cas échéant, les zones autorisées et la sortie du territoire (avec carte brune CEDEAO), et des conditions plus strictes pour le conducteur que le minimum des CGV (23 ans, 2 ans de permis).
4.2. Dépôt de garantie (sans chauffeur uniquement) : le Propriétaire choisit, pour chaque véhicule, aucun dépôt (badge « Sans caution »), une journée de location ou deux journées, dans la limite de 100 000 F CFA. Il est divisé par deux pour un client qui a fait 3 locations sans incident. Il est payé en ligne par le client avec la location et conservé par KWA-BA : le Propriétaire n'en demande aucun à la remise des clés. Le Propriétaire signale à KWA-BA tout dommage, carburant manquant ou retard constaté au retour du véhicule, photos à l'appui, dans les {{ tarifs.restitution_caution }} heures suivant la fin de la location. Seules peuvent être retenues les sommes du barème affiché (carburant manquant au prix à la pompe et forfait de 2 000 F CFA, retard, nettoyage anormal, petits dommages) ou justifiées par l'état des lieux et un devis. KWA-BA fixe le montant retenu, dans la limite du dépôt, et le verse au Propriétaire sans commission ; le solde est remboursé au client. En cas de désaccord, KWA-BA arbitre et peut retenir le montant contesté jusqu'au règlement du litige.
4.3. Aucun dépôt de garantie n'est demandé pour une location avec chauffeur.

## Article 5 – Obligations du Propriétaire
Le Propriétaire s'engage à :
1. mettre à disposition un véhicule propre, en bon état de marche et d'entretien, conforme à l'annonce, avec ses papiers à bord ;
2. détenir une assurance de responsabilité civile automobile en cours de validité couvrant la conduite par un client ou un chauffeur partenaire et, pour la location avec chauffeur, le transport de passagers dans ce cadre ; indiquer à KWA-BA, pour l'annonce, les garanties dommages éventuelles et la franchise restant à la charge du conducteur ;
3. faire l'état des lieux photographié au départ et au retour, avec le client ;
4. être joignable pendant la location ; en cas de panne non imputable au client, remplacer le véhicule ou rembourser les jours non utilisés ;
5. respecter les CGV : annulation, absence de frais pour le client, règles du dépôt de garantie, retard (tolérance de 30 minutes, puis 10 % du prix journalier par heure, journée entière au-delà de 3 heures) ;
6. transmettre à KWA-BA, dans les 3 mois, toute amende ou péage reçu pour une période de location, avec la preuve, afin qu'ils soient réclamés au client (location sans chauffeur) ou au chauffeur (infraction de conduite) ;
7. ne demander aucun paiement au client, ni caution ni complément : tout passe par la Plateforme ;
8. déclarer lui-même ses revenus.

## Article 6 – Accident, vol, dommages
6.1. Le client prévient le Propriétaire et KWA-BA au plus tard dans les 24 heures, établit un constat ou fait constater les faits, et dépose plainte en cas de vol.
6.2. Le Propriétaire déclare le sinistre à son assureur. La responsabilité du client sans chauffeur est limitée à la franchise affichée, sauf faute grave (alcool, stupéfiants, conducteur non déclaré, usage interdit, défaut de déclaration dans les 24 heures).
6.3. KWA-BA aide à réunir les preuves (photos, messages). Elle n'est ni assureur ni garante du paiement des dommages par le client.

## Article 7 – Garantie Kwa-Ba et recours
Si le client est remboursé ou reçoit un véhicule de remplacement parce que le véhicule est absent, en retard de plus d'une heure, différent de l'annonce ou en mauvais état, les sommes correspondantes sont à la charge du Propriétaire. Elles sont compensées sur ses versements suivants.

""" + COMMUN_FIN + "\n\n" + CHARTE


CHAUFFEUR = PREAMBULE + """

## Article 1 – Objet
Le Chauffeur réalise, en indépendant, des missions de conduite réservées par la Plateforme : transferts depuis ou vers l'aéroport ; voiture avec chauffeur sur le véhicule d'un propriétaire partenaire ; chauffeur pour le véhicule du client (« chauffeur exclusif »).

## Article 2 – Conditions pour exercer
– Au moins 3 ans de permis dans la catégorie du véhicule.
– Casier judiciaire ou attestation sans condamnation incompatible, de moins de 3 mois.
– Formation d'accueil Kwa-Ba.
– Le cas échéant, licence ou autorisation exigée pour le transport de personnes contre rémunération.

## Article 3 – Rémunération
– Prix payé par le client : 7 000 F CFA par jour de 10 heures au plus, pour la voiture avec chauffeur et le chauffeur seul.
– Part du Chauffeur : 6 000 F CFA par jour ; 6 500 F CFA au statut Excellence ou sur une mission qu'un client lui redemande (« Mon chauffeur »).
– Part de KWA-BA : 1 000 F CFA par jour (500 F CFA au statut Excellence ou en « Mon chauffeur »).
– Primes de déplacement, versées en totalité au Chauffeur : 1 500 F CFA par jour dans le pays hors de Lomé ; 2 000 F CFA par jour hors du pays.
– Heure supplémentaire, versée en totalité au Chauffeur : 1 000 F CFA.
– Logement et repas en cas de nuitée hors de Lomé : selon ce qui est indiqué à la réservation.
– Transfert depuis ou vers l'aéroport, assuré avec le véhicule du Chauffeur : prix du trajet affiché par la Plateforme, moins une commission de KWA-BA de {{ tarifs.commission_chauffeur }} ; le Chauffeur attend le client à la sortie avec une pancarte à son nom, soixante (60) minutes d'attente étant incluses après l'atterrissage.
– Annulation tardive par le client : la part du Chauffeur lui est versée.
– Lien Kwa-Ba Direct (propres clients du Chauffeur, dès son ouverture) : 500 F CFA par jour pour KWA-BA.
– Versement : par Mobile Money, sur un compte au nom du Chauffeur, 24 heures après la prise en charge pour un transfert, et sous 48 heures après la fin de la mission pour une mission à la journée.

## Article 4 – Règles de conduite et de service
Le Chauffeur s'engage à :
1. être ponctuel : présent à l'heure, ou prévenir immédiatement en cas d'empêchement ; un retard de plus d'une heure déclenche la recherche d'un remplaçant ;
2. respecter le code de la route ; aucune consommation d'alcool ni de stupéfiants avant ou pendant une mission ; téléphone utilisé seulement à l'arrêt ou en mains libres ;
3. avoir une tenue correcte, un comportement courtois et discret, et ne pas fumer dans le véhicule ;
4. respecter la journée de 10 heures au plus, avec des pauses raisonnables ; refuser toute demande contraire à la loi ou à la sécurité ;
5. vérifier l'état du véhicule au départ (photos) et signaler tout défaut ;
6. sur le véhicule d'un client, s'assurer que l'assurance du client couvre sa conduite ; à défaut, refuser la mission et prévenir KWA-BA ;
7. ne pas solliciter les clients, ne pas leur donner son numéro pour des missions hors Plateforme, et ne rien encaisser d'eux (pourboire seulement s'il est spontané) ;
8. ne transporter aucune autre personne ni aucun objet sans l'accord du client.

## Article 5 – Infractions et accidents
5.1. Les infractions commises par le Chauffeur au volant sont à sa charge, sauf si elles résultent d'une demande du client.
5.2. En cas d'accident, le Chauffeur assure la sécurité des passagers, prévient les secours si nécessaire, établit un constat ou fait constater les faits, et prévient immédiatement le propriétaire du véhicule et KWA-BA.

## Article 6 – Manquements
Les sanctions progressives de la charte s'appliquent, après un délai de 7 jours pour s'expliquer, notamment en cas d'absence sans prévenir, de retards répétés, de plainte fondée, de sollicitation d'un client ou de conduite dangereuse. Toute conduite sous l'emprise d'alcool ou de stupéfiants, toute violence ou tout vol entraîne l'exclusion immédiate.

## Article 7 – Indépendance
Le Chauffeur exerce son activité de manière indépendante : il reste libre d'accepter ou de refuser une mission et assume ses obligations sociales et fiscales. Le présent contrat ne crée aucun lien de subordination entre les parties.

## Annexe – Charte « Chauffeur Excellence »
– Critères d'entrée : au moins 20 missions par Kwa-Ba ; note moyenne d'au moins 4,7 sur 5 ; aucun retard de plus de 15 minutes signalé, aucune plainte fondée ni accident responsable sur les 3 derniers mois.
– Programme Fondateurs : les 10 premiers chauffeurs accèdent au statut après 10 missions au lieu de 20, s'ils remplissent les autres critères (pendant 6 mois).
– Avantages : 6 500 F CFA par jour au lieu de 6 000 (le prix client reste de 7 000) ; priorité sur le Pack Séjour et les entreprises ; badge sur le profil ; prime trimestrielle au meilleur chauffeur, d'un montant fixé par les associés.
– Révision : chaque trimestre ; le statut est perdu si un critère n'est plus rempli ou en cas d'incident grave.

""" + COMMUN_FIN + "\n\n" + CHARTE


ONG = PREAMBULE.split('\n\nLe présent contrat s')[0] + """

## Objet
Le présent contrat fixe les conditions dans lesquelles KWA-BA présente l'Association sur Kwa-Ba Give, collecte les dons des utilisateurs en sa faveur et les lui reverse.

## Présentation de l'Association
L'Association fournit des informations exactes sur son identité, son enregistrement officiel, sa mission et ses projets, ainsi que des photos dont elle détient les droits. KWA-BA vérifie ces informations avant la publication et peut retirer la page de l'Association à tout moment en cas de doute.

## Collecte et reversement
Les dons sont payés en ligne à KWA-BA, qui les conserve pour le compte de l'Association. KWA-BA ne prélève aucune commission sur les dons ; les frais de paiement sont, au choix du donateur, ajoutés à son don ou déduits de celui-ci. Les dons d'un mois sont reversés à l'Association au plus tard le {{ give.jour_reversement }} du mois suivant, aux coordonnées qu'elle a communiquées ; la preuve du reversement est publiée sur sa page.

## Engagements de l'Association
L'Association affecte les dons reçus à sa mission et, lorsqu'un projet est désigné par le donateur, à ce projet. Elle informe KWA-BA de l'avancement de ses projets et de tout changement de ses coordonnées de reversement. Elle n'utilise pas les coordonnées des donateurs, qui ne lui sont pas transmises.

## Reçus
KWA-BA adresse au donateur un reçu de paiement. KWA-BA n'étant pas habilitée à délivrer des reçus fiscaux, l'Association reste seule responsable de tout reçu fiscal qu'elle est autorisée à émettre.

""" + COMMUN_FIN


MODELES = {
    'hote': ("Contrat hôte particulier", HOTE),
    'hotel': ("Contrat hôtel et résidence hôtelière", HOTEL),
    'loueur': ("Contrat propriétaire de véhicule", LOUEUR),
    'chauffeur': ("Contrat chauffeur partenaire et charte Chauffeur Excellence", CHAUFFEUR),
    'ong': ("Convention de partenariat Kwa-Ba Give", ONG),
}
