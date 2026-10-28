from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import HebergementModel


@receiver(post_save, sender=HebergementModel, dispatch_uid='hebergements.type_par_defaut')
def type_par_defaut(sender, instance, raw=False, **kwargs):
    """Every establishment has a unit type; a single one follows the listing's price and capacity, however the
    listing is saved (host form, back-office, scripts)."""
    if raw:  # fixtures loaded as-is
        return
    from .types_logement import assurer_type_par_defaut
    assurer_type_par_defaut(instance)
