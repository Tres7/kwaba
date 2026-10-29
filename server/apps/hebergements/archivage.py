from django.db import transaction
from django.utils import timezone

from apps.notifications.infrastructure.messaging.EmailRequestBus import EmailRequestBus

from .models import HebergementModel


class ArchivageImpossible(Exception):
    pass


def archiver(hebergement: HebergementModel) -> None:
    with transaction.atomic():
        HebergementModel.objects.select_for_update().filter(pk=hebergement.pk).first()
        maintenant = timezone.now()
        if hebergement.reservations.filter(status='confirmed', check_out__gte=timezone.localdate()).exists():
            raise ArchivageImpossible(
                "Cette annonce a des séjours payés à venir ou en cours : elle ne peut pas être supprimée. Masquez-la plutôt."
            )
        en_attente = list(hebergement.reservations.filter(status='pending').select_related('guest'))
        hebergement.reservations.filter(pk__in=[r.pk for r in en_attente]).update(
            status='cancelled', annule_par='hote', annule_le=maintenant,
        )
        HebergementModel.objects.filter(pk=hebergement.pk).update(archivee_le=maintenant, is_available=False)
        hebergement.archivee_le, hebergement.is_available = maintenant, False
        for reservation in en_attente:
            transaction.on_commit(lambda r=reservation: _prevenir_voyageur(hebergement, r))


def restaurer(hebergement: HebergementModel) -> None:
    HebergementModel.tous.filter(pk=hebergement.pk).update(archivee_le=None, is_available=False)
    hebergement.archivee_le, hebergement.is_available = None, False


def _prevenir_voyageur(hebergement: HebergementModel, reservation) -> None:
    EmailRequestBus().request('hebergements.booking_cancelled_listing_removed', {
        'reservation_id': str(reservation.pk),
        'email': reservation.guest.email,
        'first_name': reservation.guest.first_name,
        'hebergement_name': hebergement.name,
        'city': hebergement.city,
        'check_in': reservation.check_in.isoformat(),
        'check_out': reservation.check_out.isoformat(),
    })
