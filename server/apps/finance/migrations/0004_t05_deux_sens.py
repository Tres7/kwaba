# T05 (refund owed to the traveller) accepts both directions, like the other partner money natures: the money of a
# payment refused (paid twice, booking cancelled meanwhile) or of a cancellation is owed to the traveller (entree),
# then leaves when the refund is sent (sortie). The file only expected « sortie », which left that money unclassified
# between the decision and the refund.
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0003_garde_fous'),
    ]

    operations = [
        migrations.RunSQL("UPDATE finance_nature SET sens_attendu = NULL WHERE code = 'T05'",
                          "UPDATE finance_nature SET sens_attendu = 'sortie' WHERE code = 'T05'"),
    ]
