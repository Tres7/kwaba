# PayPal is switched off at launch (decision of 2026-11-13): its money account and payment method exist, INACTIVE, so
# that a PayPal payment is refused by the ledger rather than left unwritten. Switching PayPal on again is a decision:
# activate these two rows (and give the account its SYSCOHADA number, with the chartered accountant).
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0005_tiers_en_texte'),
    ]

    operations = [
        migrations.RunSQL(
            ["INSERT INTO finance_compte_argent (code, libelle, type, compte_syscohada, actif) "
             "VALUES ('PAYPAL', 'Compte PayPal (euros)', 'prestataire_paiement', NULL, false)",
             "INSERT INTO finance_moyen_paiement (code, libelle, taux_frais_affiche, actif) "
             "VALUES ('PAYPAL', 'PayPal', NULL, false)"],
            ["DELETE FROM finance_moyen_paiement WHERE code = 'PAYPAL'",
             "DELETE FROM finance_compte_argent WHERE code = 'PAYPAL'"],
        ),
    ]
