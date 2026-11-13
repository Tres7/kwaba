"""Reporting views and functions of the finance module (07_Schema_base_de_donnees.sql, sections 8 and 9): every
report reads the ledger, none computes again from the bookings.

Single source of these objects. They are not in a migration: they are dropped before every `migrate` and created
again after it (signals in apps.py, ADR-024). A migration can thus change a column of the ledger without dealing with
the views that read it, and the database always has the views of the code in service.

Changes from the file, found by running its cases over two months:
- the electronic money account (55x, invariant I13) and the deposits held (I8, closing check 5) are checked on
  their CUMULATIVE balance: per month, December paying out what November collected looked like a credit balance
  and blocked the closing of a sound month;
- a day without reconciliation counts as an anomaly (FIN-02.7, « the absence of data is never a zero gap »): the
  file only counted the reconciliations already written, so a month never reconciled could be closed;
- deposits are held per booking OR per car rental (location_id): the car rental deposit is today the only real one;
- the D01 fees of the real fee rate are read with their sign, so that a corrected fee line cancels out;
- finance_synthese quotes the column of an axis (%I): an axis row is data, not code;
- invariant I10 (a line written in a locked month after its locking) is added to the control view;
- finance_sequence_piece and finance_prochain_numero are not created here: invoice numbers already come from the
  documents module (SequenceFactureModel, one lock per issue), which lot F3 extends to the other series.
"""
# Tables the views read: all created by the migration 0001 of the module
TABLES = ('finance_mouvement', 'finance_nature', 'finance_famille', 'finance_offre', 'finance_compte_argent',
          'finance_tiers_type', 'finance_periode', 'finance_rapprochement_jour', 'finance_axe')

VUES = [
    # 8.1 Signed amount, read by every view
    """
    CREATE VIEW finance_mouvement_signe AS
    SELECT m.*,
           CASE WHEN m.sens = 'entree' THEN m.montant ELSE -m.montant END AS montant_signe,
           n.famille,
           n.compte_syscohada
    FROM finance_mouvement m
    JOIN finance_nature n ON n.code = m.nature_code
    """,
    # 8.2 Revenue by type and by offer
    """
    CREATE VIEW finance_recettes_par_type AS
    SELECT mois_comptable, offre_code, nature_code, n.libelle,
           SUM(montant_signe) AS montant
    FROM finance_mouvement_signe s
    JOIN finance_nature n ON n.code = s.nature_code
    WHERE s.famille = 'R'
    GROUP BY mois_comptable, offre_code, nature_code, n.libelle
    """,
    # 8.3 Expenses by type
    """
    CREATE VIEW finance_depenses_par_type AS
    SELECT mois_comptable, offre_code, nature_code, n.libelle,
           SUM(-montant_signe) AS montant
    FROM finance_mouvement_signe s
    JOIN finance_nature n ON n.code = s.nature_code
    WHERE s.famille = 'D'
    GROUP BY mois_comptable, offre_code, nature_code, n.libelle
    """,
    # 8.4 Margin by offer: revenue of the offer less its variable costs
    """
    CREATE VIEW finance_marge_par_offre AS
    SELECT mois_comptable, offre_code,
           SUM(CASE WHEN famille = 'R' THEN montant_signe ELSE 0 END)                        AS recettes,
           SUM(CASE WHEN nature_code IN ('D01','D02','D03','D04') THEN -montant_signe ELSE 0 END) AS charges_variables,
           SUM(CASE WHEN famille = 'R' THEN montant_signe ELSE 0 END)
             - SUM(CASE WHEN nature_code IN ('D01','D02','D03','D04') THEN -montant_signe ELSE 0 END) AS marge
    FROM finance_mouvement_signe
    GROUP BY mois_comptable, offre_code
    """,
    # 8.5 Sums owed to the partners (FIN-04.1, invariant I4)
    """
    CREATE VIEW finance_du_aux_partenaires AS
    SELECT tiers_type, tiers_id,
           SUM(montant_signe) AS solde_du
    FROM finance_mouvement_signe
    WHERE famille = 'T'
    GROUP BY tiers_type, tiers_id
    HAVING SUM(montant_signe) <> 0
    """,
    # 8.6 Deposits held (invariant I8), per booking or per car rental
    """
    CREATE VIEW finance_cautions_detenues AS
    SELECT reservation_id, location_id,
           SUM(montant_signe) AS solde_detenu
    FROM finance_mouvement_signe
    WHERE famille = 'C'
    GROUP BY reservation_id, location_id
    HAVING SUM(montant_signe) <> 0
    """,
    # 8.7 Balance by money account (invariant I5)
    """
    CREATE VIEW finance_solde_compte_argent AS
    SELECT compte_argent_code,
           SUM(montant_signe) AS solde_livre
    FROM finance_mouvement_signe
    GROUP BY compte_argent_code
    """,
    # 8.8 Real payment fee rate (FIN-12.3)
    """
    CREATE VIEW finance_taux_frais_reel AS
    SELECT mois_comptable,
           SUM(CASE WHEN nature_code = 'D01' THEN -montant_signe ELSE 0 END)                 AS frais,
           SUM(CASE WHEN famille = 'R' THEN montant_signe ELSE 0 END)                        AS revenu,
           SUM(CASE WHEN sens = 'entree' AND famille IN ('R','T','C') THEN montant ELSE 0 END) AS volume_encaisse,
           ROUND(100.0 * SUM(CASE WHEN nature_code = 'D01' THEN -montant_signe ELSE 0 END)
                 / NULLIF(SUM(CASE WHEN famille = 'R' THEN montant_signe ELSE 0 END), 0), 2) AS pct_du_revenu
    FROM finance_mouvement_signe
    GROUP BY mois_comptable
    """,
    # 8.9 Double entry (AUDCIF art. 17-2): each movement gives two lines of the same amount and opposite directions,
    # the account of its nature (the collective account of its kind of third party for the T family) and, as the
    # counterpart, the account of the money account
    """
    CREATE VIEW finance_ecriture AS
    WITH base AS (
        SELECT m.id, m.date_evenement, m.mois_comptable, m.montant, m.devise,
               m.sens, m.nature_code, m.offre_code, m.piece_reference,
               m.tiers_type, m.tiers_id, m.moyen_paiement_code, m.compte_argent_code,
               m.reservation_id, m.annule_mouvement_id,
               n.famille, n.libelle AS nature_libelle,
               CASE WHEN n.famille = 'T' THEN COALESCE(tt.compte_syscohada, n.compte_syscohada)
                    ELSE n.compte_syscohada END               AS compte_nature,
               c.compte_syscohada AS compte_contrepartie, c.libelle AS compte_argent_libelle
        FROM finance_mouvement m
        JOIN finance_nature n       ON n.code = m.nature_code
        JOIN finance_compte_argent c ON c.code = m.compte_argent_code
        LEFT JOIN finance_tiers_type tt ON tt.code = m.tiers_type
        WHERE COALESCE(CASE WHEN n.famille = 'T' THEN tt.compte_syscohada END,
                       n.compte_syscohada) IS NOT NULL
          AND c.compte_syscohada IS NOT NULL
    )
    SELECT b.mois_comptable,
           b.date_evenement::date AS date_ecriture,
           CASE b.famille
                WHEN 'R' THEN 'VT'
                WHEN 'D' THEN 'AC'
                WHEN 'I' THEN 'OD'
                WHEN 'F' THEN 'OD'
                WHEN 'V' THEN 'TR'
                ELSE 'TR' END                                   AS journal,
           b.id                                                 AS mouvement_id,
           l.ligne                                              AS ligne_ecriture,
           CASE l.ligne WHEN 1 THEN b.compte_nature
                        ELSE b.compte_contrepartie END          AS compte_general,
           CASE WHEN l.ligne = 1 AND b.tiers_type IS NOT NULL AND b.tiers_id IS NOT NULL
                THEN upper(b.tiers_type) || '-' || b.tiers_id::text
                ELSE NULL END                                   AS compte_auxiliaire,
           b.piece_reference                                    AS piece,
           CASE l.ligne WHEN 1 THEN b.nature_libelle
                        ELSE b.compte_argent_libelle END
                || CASE WHEN b.piece_reference IS NULL THEN ''
                        ELSE ' — ' || b.piece_reference END      AS libelle,
           CASE WHEN (l.ligne = 1 AND b.sens = 'sortie')
                  OR (l.ligne = 2 AND b.sens = 'entree')
                THEN b.montant ELSE 0 END                       AS debit,
           CASE WHEN (l.ligne = 1 AND b.sens = 'entree')
                  OR (l.ligne = 2 AND b.sens = 'sortie')
                THEN b.montant ELSE 0 END                       AS credit,
           b.devise, b.moyen_paiement_code, b.compte_argent_code,
           b.offre_code, b.nature_code, b.famille,
           b.reservation_id, b.annule_mouvement_id
    FROM base b
    CROSS JOIN (VALUES (1), (2)) AS l(ligne)
    """,
    # File of accounting entries for the accounting firm, and for the tax office in case of an audit
    """
    CREATE VIEW finance_export_comptable AS
    SELECT * FROM finance_ecriture ORDER BY date_ecriture, mouvement_id, ligne_ecriture
    """,
    # The three books of article 19: journal, general ledger by account, trial balance
    """
    CREATE VIEW finance_livre_journal AS
    SELECT date_ecriture, journal, mouvement_id, ligne_ecriture,
           compte_general, compte_auxiliaire, piece, libelle, debit, credit, devise
    FROM finance_ecriture
    ORDER BY date_ecriture, journal, mouvement_id, ligne_ecriture
    """,
    """
    CREATE VIEW finance_grand_livre AS
    SELECT compte_general, compte_auxiliaire, mois_comptable, date_ecriture,
           journal, mouvement_id, piece, libelle, debit, credit,
           SUM(debit - credit) OVER (PARTITION BY compte_general
                                     ORDER BY date_ecriture, mouvement_id, ligne_ecriture
                                     ROWS UNBOUNDED PRECEDING) AS solde_progressif
    FROM finance_ecriture
    ORDER BY compte_general, date_ecriture, mouvement_id, ligne_ecriture
    """,
    """
    CREATE VIEW finance_balance_generale AS
    SELECT mois_comptable, compte_general,
           count(*)                       AS nb_lignes,
           SUM(debit)                     AS total_debit,
           SUM(credit)                    AS total_credit,
           SUM(debit) - SUM(credit)       AS solde
    FROM finance_ecriture
    GROUP BY mois_comptable, compte_general
    ORDER BY mois_comptable, compte_general
    """,
    # Balance check (I11): the debits equal the credits
    """
    CREATE VIEW finance_controle_equilibre AS
    SELECT mois_comptable,
           SUM(debit)  AS total_debit,
           SUM(credit) AS total_credit,
           SUM(debit) - SUM(credit) AS ecart
    FROM finance_ecriture
    GROUP BY mois_comptable
    ORDER BY mois_comptable
    """,
    # Movements no entry can represent, for lack of a SYSCOHADA account (I12): must stay empty before any closing
    """
    CREATE VIEW finance_ecritures_sans_compte AS
    SELECT m.id, m.mois_comptable, m.date_evenement, m.montant, m.nature_code,
           n.libelle AS nature_libelle, m.compte_argent_code,
           CASE WHEN COALESCE(CASE WHEN n.famille = 'T' THEN tt.compte_syscohada END, n.compte_syscohada) IS NULL
                THEN 'nature sans compte SYSCOHADA'
                ELSE 'compte d''argent sans compte SYSCOHADA' END AS motif
    FROM finance_mouvement m
    JOIN finance_nature n ON n.code = m.nature_code
    LEFT JOIN finance_compte_argent c ON c.code = m.compte_argent_code
    LEFT JOIN finance_tiers_type tt ON tt.code = m.tiers_type
    WHERE COALESCE(CASE WHEN n.famille = 'T' THEN tt.compte_syscohada END,
                   n.compte_syscohada) IS NULL
       OR c.compte_syscohada IS NULL
    """,
    # 8.10 Control screen of the invariants (specification, section 4)
    """
    CREATE VIEW finance_controle_invariants AS
    WITH i5 AS (
        -- Every day since the first movement, up to yesterday, reconciled with a zero gap on each active account
        SELECT count(*) AS n
        FROM finance_compte_argent c
        CROSS JOIN generate_series((SELECT min(date_evenement)::date FROM finance_mouvement)::timestamp,
                                   (current_date - 1)::timestamp, interval '1 day') AS j(jour)
        WHERE c.actif
          AND NOT EXISTS (SELECT 1 FROM finance_rapprochement_jour r
                          WHERE r.jour = j.jour::date AND r.compte_argent_code = c.code
                            AND r.etat = 'fait' AND r.ecart = 0)
    ), i8 AS (
        SELECT count(*) AS n FROM (
            SELECT reservation_id, location_id
            FROM finance_mouvement_signe WHERE famille = 'C'
            GROUP BY reservation_id, location_id HAVING SUM(montant_signe) < 0
        ) x
    ), i9 AS (
        SELECT count(*) AS n FROM finance_mouvement
        WHERE nature_code IS NULL OR offre_code IS NULL
    ), i10 AS (
        SELECT count(*) AS n
        FROM finance_mouvement m
        JOIN finance_periode p ON p.mois = m.mois_comptable
        WHERE p.etat = 'verrouillee' AND p.verrouillee_le IS NOT NULL AND m.cree_le > p.verrouillee_le
    ), i11 AS (
        SELECT count(*) AS n FROM finance_controle_equilibre WHERE ecart <> 0
    ), i12 AS (
        SELECT count(*) AS n FROM finance_ecritures_sans_compte
    ), i13 AS (
        -- SYSCOHADA rule: an electronic money account (55x) is debit or zero, on its cumulative balance
        SELECT count(*) AS n FROM (
            SELECT compte_general FROM finance_ecriture
            WHERE compte_general LIKE '55%'
            GROUP BY compte_general HAVING SUM(debit) - SUM(credit) < 0
        ) x
    )
    SELECT 'I5' AS invariant, 'Rapprochement fait et écart nul, chaque jour' AS libelle, (SELECT n FROM i5) AS anomalies
    UNION ALL SELECT 'I8', 'Cautions détenues jamais négatives',              (SELECT n FROM i8)
    UNION ALL SELECT 'I9', 'Aucune ligne sans nature ni offre',               (SELECT n FROM i9)
    UNION ALL SELECT 'I10', 'Aucune écriture dans un mois verrouillé',        (SELECT n FROM i10)
    UNION ALL SELECT 'I11', 'Débits égaux aux crédits (AUDCIF art. 17-2)',    (SELECT n FROM i11)
    UNION ALL SELECT 'I12', 'Tout mouvement porte un compte SYSCOHADA',       (SELECT n FROM i12)
    UNION ALL SELECT 'I13', 'Monnaie électronique jamais créditrice (55x)',   (SELECT n FROM i13)
    """,
    # 9.1 The single view every report reads
    """
    CREATE VIEW finance_pivot AS
    SELECT
        m.id,
        m.date_evenement,
        m.mois_comptable,
        to_char(m.mois_comptable, 'YYYY')        AS annee,
        to_char(m.mois_comptable, 'YYYY-MM')     AS mois,
        n.famille,
        f.libelle                                AS famille_libelle,
        m.nature_code,
        n.libelle                                AS nature_libelle,
        n.compte_syscohada,
        m.offre_code,
        o.libelle                                AS offre_libelle,
        m.tiers_type,
        m.tiers_id,
        m.moyen_paiement_code,
        m.compte_argent_code,
        m.prestation_type,
        m.piece_reference,
        m.devise,
        m.metadonnees,
        m.montant,
        CASE WHEN m.sens = 'entree' THEN m.montant ELSE -m.montant END AS montant_signe
    FROM finance_mouvement m
    JOIN finance_nature  n ON n.code = m.nature_code
    JOIN finance_famille f ON f.code = n.famille
    JOIN finance_offre   o ON o.code = m.offre_code
    """,
]

FONCTIONS = [
    # « Can I close this month? »: one row per check, OK or REFUSE, and what to do. One REFUSE forbids the locking.
    """
    CREATE FUNCTION finance_peut_on_cloturer(p_mois date)
    RETURNS TABLE (controle text, resultat text, verdict text, que_faire text)
    LANGUAGE sql STABLE AS $$
    WITH c AS (
        SELECT 1 AS rang,
               'Equilibre des ecritures (AUDCIF art. 17-2)' AS controle,
               COALESCE((SELECT ecart FROM finance_controle_equilibre
                         WHERE mois_comptable = p_mois), 0) AS valeur,
               'Reprendre finance_controle_equilibre et identifier le mouvement fautif' AS que_faire
        UNION ALL SELECT 2, 'Mouvements sans compte SYSCOHADA',
               (SELECT count(*) FROM finance_ecritures_sans_compte WHERE mois_comptable = p_mois),
               'Completer le compte de la nature concernee, ou du compte d''argent'
        UNION ALL SELECT 3, 'Monnaie electronique non creditrice (55x)',
               (SELECT count(*) FROM (
                    SELECT compte_general FROM finance_ecriture
                    WHERE mois_comptable <= p_mois AND compte_general LIKE '55%'
                    GROUP BY compte_general HAVING SUM(debit) - SUM(credit) < 0) x),
               'Un solde 55 negatif signale un encaissement manquant ou un double decaissement'
        UNION ALL SELECT 4, 'Rapprochement du prestataire de paiement',
               (SELECT count(*)
                FROM generate_series(p_mois::timestamp, (p_mois + interval '1 month' - interval '1 day'),
                                     interval '1 day') AS j(jour)
                CROSS JOIN finance_compte_argent ca
                WHERE ca.actif
                  AND NOT EXISTS (SELECT 1 FROM finance_rapprochement_jour r
                                  WHERE r.jour = j.jour::date AND r.compte_argent_code = ca.code
                                    AND r.etat = 'fait' AND r.ecart = 0)),
               'Rapprocher les journees restantes avant de cloturer : une journee sans rapprochement n''est jamais un ecart nul'
        UNION ALL SELECT 5, 'Cautions detenues jamais negatives',
               (SELECT count(*) FROM (
                    SELECT reservation_id, location_id FROM finance_mouvement_signe
                    WHERE famille = 'C' AND mois_comptable <= p_mois
                    GROUP BY reservation_id, location_id HAVING SUM(montant_signe) < 0) x),
               'Une caution restituee au-dela de ce qui a ete recu : verifier la reservation'
        UNION ALL SELECT 6, 'Toute ligne porte une nature et une offre',
               (SELECT count(*) FROM finance_mouvement
                WHERE mois_comptable = p_mois AND (nature_code IS NULL OR offre_code IS NULL)),
               'Qualifier les lignes incompletes avant cloture'
    )
    SELECT controle,
           CASE WHEN rang = 1 THEN 'ecart de ' || valeur::text || ' F'
                ELSE valeur::text || ' anomalie(s)' END,
           CASE WHEN valeur = 0 THEN 'OK' ELSE 'REFUSE' END,
           CASE WHEN valeur = 0 THEN '—' ELSE que_faire END
    FROM c ORDER BY rang;
    $$
    """,
    # 9.4 The single engine of the reports, present and future: a GROUP BY of finance_pivot on one or two axes
    """
    CREATE OR REPLACE FUNCTION finance_synthese(
        p_debut     date,
        p_fin       date,
        p_axe1      text DEFAULT 'mois',
        p_axe2      text DEFAULT NULL,
        p_familles  text[] DEFAULT NULL,
        p_offres    text[] DEFAULT NULL
    )
    RETURNS TABLE (axe1 text, axe2 text, nb bigint, montant bigint)
    LANGUAGE plpgsql STABLE AS $fn$
    DECLARE
        c1 text;
        c2 text;
    BEGIN
        -- The columns come from the axes table, quoted as identifiers: no injection possible
        SELECT colonne INTO c1 FROM finance_axe WHERE code = p_axe1 AND actif;
        IF c1 IS NULL THEN
            RAISE EXCEPTION 'axe inconnu : %. Voir la table finance_axe.', p_axe1;
        END IF;
        IF p_axe2 IS NOT NULL THEN
            SELECT colonne INTO c2 FROM finance_axe WHERE code = p_axe2 AND actif;
            IF c2 IS NULL THEN
                RAISE EXCEPTION 'axe inconnu : %. Voir la table finance_axe.', p_axe2;
            END IF;
        END IF;

        RETURN QUERY EXECUTE format(
            'SELECT %I::text, %s::text, count(*)::bigint, sum(montant_signe)::bigint
               FROM finance_pivot
              WHERE date_evenement >= $1 AND date_evenement < ($2::date + 1)
                AND ($3 IS NULL OR famille    = ANY($3))
                AND ($4 IS NULL OR offre_code = ANY($4))
              GROUP BY 1, 2
              ORDER BY 1, 2',
            c1, CASE WHEN c2 IS NULL THEN 'NULL' ELSE quote_ident(c2) END)
        USING p_debut, p_fin, p_familles, p_offres;
    END $fn$
    """,
]

SUPPRESSION = [
    'DROP FUNCTION IF EXISTS finance_synthese(date, date, text, text, text[], text[])',
    'DROP FUNCTION IF EXISTS finance_peut_on_cloturer(date)',
    'DROP VIEW IF EXISTS finance_pivot CASCADE',
    'DROP VIEW IF EXISTS finance_controle_invariants CASCADE',
    'DROP VIEW IF EXISTS finance_ecritures_sans_compte CASCADE',
    'DROP VIEW IF EXISTS finance_controle_equilibre CASCADE',
    'DROP VIEW IF EXISTS finance_balance_generale CASCADE',
    'DROP VIEW IF EXISTS finance_grand_livre CASCADE',
    'DROP VIEW IF EXISTS finance_livre_journal CASCADE',
    'DROP VIEW IF EXISTS finance_export_comptable CASCADE',
    'DROP VIEW IF EXISTS finance_ecriture CASCADE',
    'DROP VIEW IF EXISTS finance_taux_frais_reel CASCADE',
    'DROP VIEW IF EXISTS finance_solde_compte_argent CASCADE',
    'DROP VIEW IF EXISTS finance_cautions_detenues CASCADE',
    'DROP VIEW IF EXISTS finance_du_aux_partenaires CASCADE',
    'DROP VIEW IF EXISTS finance_marge_par_offre CASCADE',
    'DROP VIEW IF EXISTS finance_depenses_par_type CASCADE',
    'DROP VIEW IF EXISTS finance_recettes_par_type CASCADE',
    'DROP VIEW IF EXISTS finance_mouvement_signe CASCADE',
]


def supprimer(curseur) -> None:
    for sql in SUPPRESSION:
        curseur.execute(sql)


def creer(curseur) -> None:
    """Drops then creates every view and function, in dependency order."""
    supprimer(curseur)
    for sql in VUES + FONCTIONS:
        curseur.execute(sql)


def avant_migration(sender, using='default', **kwargs) -> None:
    """pre_migrate: no view stands in the way of a migration of the ledger's columns."""
    from django.db import connections

    with connections[using].cursor() as curseur:
        supprimer(curseur)


def apres_migration(sender, using='default', **kwargs) -> None:
    """post_migrate: the views and functions of the code in service, once the tables exist (not after
    `migrate finance zero`)."""
    from django.db import connections

    connexion = connections[using]
    if not set(TABLES) <= set(connexion.introspection.table_names()):
        return
    with connexion.cursor() as curseur:
        creer(curseur)
