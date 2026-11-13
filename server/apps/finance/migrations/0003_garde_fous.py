# Guards of the ledger in the database itself (07_Schema_base_de_donnees.sql, sections 3.1 and 3.2): the refusals hold
# whoever writes, the application, a script or an administrator in psql.
#
# Changes from the file, all stricter or needed to apply its own rules:
# - an unknown code (nature, offer, account, kind of third party, method) is refused at once: Django declares its
#   foreign keys DEFERRABLE, which would postpone the refusal to the commit;
# - an inactive offer, money account, kind of third party or method is refused like an inactive nature (FIN-01.4);
# - a correction (annule_mouvement_id) skips the expected direction of its nature: an inverse line is in the other
#   direction by definition, and the file's trigger refused the correction of any R or T line (case FB-03). It must
#   take back the nature, offer, third party, account and amount of the line it cancels, and cannot itself be
#   corrected;
# - the history of parameters and of accounting correspondence is append only as well (FIN-16.5, FIN-07.3).
from django.db import migrations

AJOUT_SEUL = [
    """
    CREATE OR REPLACE FUNCTION finance_mouvement_ajout_seul()
    RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
        RAISE EXCEPTION
            'finance_mouvement est en ajout seul : % refusée sur la ligne %. Passez une ligne inverse (annule_mouvement_id).',
            TG_OP, COALESCE(OLD.id, 0);
    END $$
    """,
    """
    CREATE TRIGGER trg_finance_mouvement_ajout_seul
        BEFORE UPDATE OR DELETE ON finance_mouvement
        FOR EACH ROW EXECUTE FUNCTION finance_mouvement_ajout_seul()
    """,
    """
    CREATE OR REPLACE FUNCTION finance_historique_ajout_seul()
    RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
        RAISE EXCEPTION '% est en ajout seul : % refusée', TG_TABLE_NAME, TG_OP;
    END $$
    """,
    """
    CREATE TRIGGER trg_finance_parametre_histo_ajout_seul
        BEFORE UPDATE OR DELETE ON finance_parametre_histo
        FOR EACH ROW EXECUTE FUNCTION finance_historique_ajout_seul()
    """,
    """
    CREATE TRIGGER trg_finance_correspondance_histo_ajout_seul
        BEFORE UPDATE OR DELETE ON finance_correspondance_histo
        FOR EACH ROW EXECUTE FUNCTION finance_historique_ajout_seul()
    """,
]

CONTROLES = [
    """
    CREATE OR REPLACE FUNCTION finance_mouvement_controles()
    RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE
        v_etat          text;
        v_sens_attendu  text;
        v_actif         boolean;
        v_corrigee      finance_mouvement%ROWTYPE;
    BEGIN
        -- The accounting month is the month of the event, except for inventory entries
        IF date_trunc('month', NEW.date_evenement)::date <> NEW.mois_comptable
           AND NEW.origine <> 'calcul' THEN
            RAISE EXCEPTION 'mois_comptable (%) incohérent avec date_evenement (%)',
                NEW.mois_comptable, NEW.date_evenement;
        END IF;

        -- FIN-08.1: no writing in a locked month
        SELECT etat INTO v_etat FROM finance_periode WHERE mois = NEW.mois_comptable;
        IF v_etat IS NULL THEN
            RAISE EXCEPTION 'période comptable % non ouverte', NEW.mois_comptable;
        END IF;
        IF v_etat = 'verrouillee' THEN
            RAISE EXCEPTION 'période % verrouillée : écriture refusée', NEW.mois_comptable;
        END IF;

        -- Correction: an inverse line of the line it cancels (FIN-01.3)
        IF NEW.annule_mouvement_id IS NOT NULL THEN
            IF NEW.motif IS NULL OR length(trim(NEW.motif)) = 0 THEN
                RAISE EXCEPTION 'une ligne inverse exige un motif';
            END IF;
            SELECT * INTO v_corrigee FROM finance_mouvement WHERE id = NEW.annule_mouvement_id;
            IF v_corrigee.id IS NULL THEN
                RAISE EXCEPTION 'ligne % inconnue : rien à corriger', NEW.annule_mouvement_id;
            END IF;
            IF v_corrigee.annule_mouvement_id IS NOT NULL THEN
                RAISE EXCEPTION 'la ligne % est elle-même une correction : passez une nouvelle ligne',
                    NEW.annule_mouvement_id;
            END IF;
            IF NEW.sens = v_corrigee.sens OR NEW.montant <> v_corrigee.montant
               OR NEW.nature_code <> v_corrigee.nature_code OR NEW.offre_code <> v_corrigee.offre_code
               OR NEW.compte_argent_code <> v_corrigee.compte_argent_code
               OR NEW.tiers_type IS DISTINCT FROM v_corrigee.tiers_type
               OR NEW.tiers_id IS DISTINCT FROM v_corrigee.tiers_id THEN
                RAISE EXCEPTION 'la ligne inverse doit reprendre la nature, l''offre, le tiers, le compte et le montant de la ligne %, en sens opposé',
                    NEW.annule_mouvement_id;
            END IF;
            RETURN NEW;
        END IF;

        -- FIN-01.4: known and active nature, direction as expected
        SELECT sens_attendu, actif INTO v_sens_attendu, v_actif
        FROM finance_nature WHERE code = NEW.nature_code;
        IF v_actif IS NULL THEN
            RAISE EXCEPTION 'nature % inconnue : écriture refusée', NEW.nature_code;
        END IF;
        IF NOT v_actif THEN
            RAISE EXCEPTION 'nature % inactive : écriture refusée', NEW.nature_code;
        END IF;
        IF v_sens_attendu IS NOT NULL AND v_sens_attendu <> NEW.sens THEN
            RAISE EXCEPTION 'nature % attend le sens %, reçu %',
                NEW.nature_code, v_sens_attendu, NEW.sens;
        END IF;

        -- Known and active offer, money account, kind of third party and payment method
        SELECT active INTO v_actif FROM finance_offre WHERE code = NEW.offre_code;
        IF v_actif IS NULL THEN
            RAISE EXCEPTION 'offre % inconnue : écriture refusée', NEW.offre_code;
        END IF;
        IF NOT v_actif THEN
            RAISE EXCEPTION 'offre % non ouverte : écriture refusée', NEW.offre_code;
        END IF;
        SELECT actif INTO v_actif FROM finance_compte_argent WHERE code = NEW.compte_argent_code;
        IF v_actif IS NULL THEN
            RAISE EXCEPTION 'compte d''argent % inconnu : écriture refusée', NEW.compte_argent_code;
        END IF;
        IF NOT v_actif THEN
            RAISE EXCEPTION 'compte d''argent % inactif : écriture refusée', NEW.compte_argent_code;
        END IF;
        IF NEW.tiers_type IS NOT NULL THEN
            SELECT actif INTO v_actif FROM finance_tiers_type WHERE code = NEW.tiers_type;
            IF v_actif IS NULL OR NOT v_actif THEN
                RAISE EXCEPTION 'type de tiers % inconnu ou inactif : écriture refusée', NEW.tiers_type;
            END IF;
        END IF;
        IF NEW.moyen_paiement_code IS NOT NULL THEN
            SELECT actif INTO v_actif FROM finance_moyen_paiement WHERE code = NEW.moyen_paiement_code;
            IF v_actif IS NULL OR NOT v_actif THEN
                RAISE EXCEPTION 'moyen de paiement % inconnu ou inactif : écriture refusée', NEW.moyen_paiement_code;
            END IF;
        END IF;

        -- C03 needs the reason and the reference of the decision
        IF NEW.nature_code = 'C03' AND (NEW.motif IS NULL OR length(trim(NEW.motif)) = 0) THEN
            RAISE EXCEPTION 'C03 (caution retenue) exige un motif et la référence de la décision';
        END IF;

        RETURN NEW;
    END $$
    """,
    """
    CREATE TRIGGER trg_finance_mouvement_controles
        BEFORE INSERT ON finance_mouvement
        FOR EACH ROW EXECUTE FUNCTION finance_mouvement_controles()
    """,
]

INVERSE = [
    'DROP TRIGGER IF EXISTS trg_finance_mouvement_controles ON finance_mouvement',
    'DROP FUNCTION IF EXISTS finance_mouvement_controles()',
    'DROP TRIGGER IF EXISTS trg_finance_correspondance_histo_ajout_seul ON finance_correspondance_histo',
    'DROP TRIGGER IF EXISTS trg_finance_parametre_histo_ajout_seul ON finance_parametre_histo',
    'DROP FUNCTION IF EXISTS finance_historique_ajout_seul()',
    'DROP TRIGGER IF EXISTS trg_finance_mouvement_ajout_seul ON finance_mouvement',
    'DROP FUNCTION IF EXISTS finance_mouvement_ajout_seul()',
]


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0002_referentiels'),
    ]

    operations = [
        migrations.RunSQL(AJOUT_SEUL + CONTROLES, INVERSE),
    ]
