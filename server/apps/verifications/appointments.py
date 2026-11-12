import uuid
from datetime import timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.agenda import api as agenda
from apps.hebergements import api as hebergements
from apps.terrain import api as terrain
from apps.users import api as users

from . import services
from .models import VisitInvitationModel

MISSION_TYPE = 'logement'
WEEKDAYS = ['lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi', 'dimanche']


class AppointmentError(Exception):
    def __init__(self, message: str, code: int = 400):
        super().__init__(message)
        self.code = code


def _from_agenda(exc: agenda.AgendaError) -> AppointmentError:
    return AppointmentError(str(exc), exc.code)


def _restart_invitations(listing_ids) -> None:
    VisitInvitationModel.objects.filter(listing_id__in=list(listing_ids)).update(
        invited_at=timezone.now(), reminded_at=None, alerted_at=None)


def _host_listings(host_id) -> dict[str, dict]:
    return {str(a['id']): a for a in services.annonces_a_visiter() if a['host_id'] == host_id}


def _movable(appointment) -> bool:
    notice = timedelta(hours=agenda.settings().notice_hours)
    return appointment.status == 'confirmed' and appointment.start - notice > timezone.now()


def host_appointment_json(appointment) -> dict:
    return {**agenda.summary(appointment), 'movable': _movable(appointment)}


def listings_to_schedule(host) -> list[dict]:
    listings = _host_listings(host.pk)
    booked = {t.id: a for a in agenda.confirmed_for_targets(listings) for t in a.targets}
    return [{
        'id': key, 'name': listing['name'], 'city': listing['city'], 'address': listing['location'],
        'image_url': listing['image_url'],
        'has_position': listing['latitude'] is not None and listing['longitude'] is not None,
        'appointment': host_appointment_json(booked[key]) if key in booked else None,
    } for key, listing in listings.items()]


def _selection(host_id, listing_ids) -> list[dict]:
    ids = [str(i) for i in listing_ids]
    if not ids or len(set(ids)) != len(ids):
        raise AppointmentError("Choisissez une ou plusieurs annonces.")
    listings = _host_listings(host_id)
    if any(i not in listings for i in ids):
        raise AppointmentError("Une de ces annonces n'attend pas de visite.", 404)
    chosen = [listings[i] for i in ids]
    if len({' '.join((c['city'] or '').casefold().split()) for c in chosen}) > 1:
        raise AppointmentError("Une visite groupée réunit des annonces de la même ville.")
    return chosen


def _assigned_agent(listings: list[dict]) -> uuid.UUID | None:
    agents = {m.agent_id for m in (terrain.en_cours(MISSION_TYPE, str(c['id'])) for c in listings) if m}
    if len(agents) > 1:
        raise AppointmentError("Ces annonces sont suivies par des agents différents : réservez-les séparément.", 409)
    return next(iter(agents), None)


def _coordinate(value):
    return None if value is None else float(value)


def _targets(listings: list[dict]) -> list:
    return [agenda.Target(id=str(c['id']), title=c['name'], latitude=_coordinate(c['latitude']),
                          longitude=_coordinate(c['longitude'])) for c in listings]


def _waiting_since(listings: list[dict]):
    invitations = VisitInvitationModel.objects.filter(listing_id__in=[c['id'] for c in listings])
    return min([i.invited_at for i in invitations] or [c['created_at'] for c in listings])


def _request(host_id, listings, start, agent_id=None):
    return agenda.BookingRequest(
        requester_id=host_id, city=listings[0]['city'], targets=_targets(listings), start=start,
        address=listings[0]['location'] or '', agent_id=agent_id, waiting_since=_waiting_since(listings))


def free_slots(host, listing_ids) -> list:
    listings = _selection(host.pk, listing_ids)
    try:
        return agenda.free_slots(listings[0]['city'], len(listings), _assigned_agent(listings))
    except agenda.AgendaError as exc:
        raise _from_agenda(exc) from None


def free_slots_to_move(host, appointment_id) -> list:
    try:
        appointment = agenda.appointment(appointment_id)
    except agenda.AgendaError as exc:
        raise _from_agenda(exc) from None
    if appointment.requester_id != host.pk:
        raise AppointmentError("Rendez-vous introuvable.", 404)
    return agenda.free_slots(appointment.city, len(appointment.targets), appointment.agent_id,
                             exclude=appointment.id)


def _take_missions(listing_ids, agent_id) -> None:
    agent = users.compte(agent_id)
    for listing_id in listing_ids:
        try:
            terrain.prendre(MISSION_TYPE, str(listing_id), agent)
        except terrain.MissionErreur as exc:
            raise AppointmentError(str(exc), exc.code) from None


def _release_missions(appointment, user) -> None:
    for target in appointment.targets:
        mission = terrain.en_cours(MISSION_TYPE, target.id)
        if mission and mission.agent_id == appointment.agent_id:
            terrain.liberer(MISSION_TYPE, target.id, user)


@transaction.atomic
def book(host, listing_ids, start):
    listings = _selection(host.pk, listing_ids)
    try:
        appointment = agenda.book(_request(host.pk, listings, start, _assigned_agent(listings)))
    except agenda.AgendaError as exc:
        raise _from_agenda(exc) from None
    _take_missions([c['id'] for c in listings], appointment.agent_id)
    return appointment


@transaction.atomic
def book_by_phone(agent, listing_ids, start):
    first = str(next(iter(listing_ids), ''))
    listing = next((c for c in services.annonces_a_visiter() if str(c['id']) == first), None)
    if listing is None:
        raise AppointmentError("Cette annonce n'attend pas de visite.", 404)
    if listing['host_id'] == agent.pk:
        raise AppointmentError("Un autre agent doit vérifier votre propre annonce.", 403)
    listings = _selection(listing['host_id'], listing_ids)
    assigned = _assigned_agent(listings)
    if assigned and assigned != agent.pk:
        raise AppointmentError("Un autre agent s'occupe de cette annonce.", 409)
    try:
        appointment = agenda.book_by_phone(agent.pk, _request(listing['host_id'], listings, start))
    except agenda.AgendaError as exc:
        raise _from_agenda(exc) from None
    _take_missions([c['id'] for c in listings], agent.pk)
    return appointment


def move(host, appointment_id, start):
    try:
        return agenda.move(appointment_id, host.pk, start)
    except agenda.AgendaError as exc:
        raise _from_agenda(exc) from None


@transaction.atomic
def cancel(user, appointment_id, reason: str):
    by = agenda.BY_ADMIN if user.role == 'admin' else agenda.BY_AGENT
    try:
        appointment = agenda.cancel(appointment_id, author_id=user.pk, by=by, reason=reason)
    except agenda.AgendaError as exc:
        raise _from_agenda(exc) from None
    _release_missions(appointment, user)
    _restart_invitations(t.id for t in appointment.targets)
    return appointment


@transaction.atomic
def reassign(admin, appointment_id, agent_id):
    try:
        new_agent = users.compte(uuid.UUID(str(agent_id)))
    except ValueError:
        new_agent = None
    if new_agent is None or new_agent.role not in ('agent', 'admin') or not new_agent.is_active:
        raise AppointmentError("Agent inconnu.", 404)
    try:
        before = agenda.appointment(appointment_id)
        appointment = agenda.reassign(appointment_id, new_agent.pk)
    except agenda.AgendaError as exc:
        raise _from_agenda(exc) from None
    if appointment.agent_id != before.agent_id:
        _release_missions(before, admin)
        _take_missions([t.id for t in appointment.targets], new_agent.pk)
    return appointment


def _name(account) -> str:
    return (account.get_full_name() or account.email) if account else '-'


def _hosts_without_appointment(now) -> tuple[list, list]:
    config = agenda.settings()
    remind_after = timedelta(days=config.host_reminder_days)
    alert_after = timedelta(days=config.host_alert_days)
    invitations = list(VisitInvitationModel.objects.filter(invited_at__lte=now - remind_after).exclude(
        reminded_at__isnull=False, alerted_at__isnull=False))
    if not invitations:
        return [], []
    waiting = {str(c['id']): c for c in services.annonces_a_visiter()}
    booked = {t.id for a in agenda.confirmed_for_targets([i.listing_id for i in invitations]) for t in a.targets}
    to_remind, to_alert = [], []
    for invitation in invitations:
        key = str(invitation.listing_id)
        if key not in waiting:
            invitation.delete()
            continue
        if key in booked:
            continue
        if invitation.reminded_at is None:
            to_remind.append((invitation, waiting[key]))
        if invitation.alerted_at is None and invitation.invited_at <= now - alert_after:
            to_alert.append((invitation, waiting[key]))
    return to_remind, to_alert


def remind_hosts() -> dict:
    now = timezone.now()
    to_remind, to_alert = _hosts_without_appointment(now)
    for invitation, listing in to_remind:
        with transaction.atomic():
            VisitInvitationModel.objects.filter(pk=invitation.pk).update(reminded_at=now)
            host = users.compte(listing['host_id'])
            if host:
                services._envoyer('booking_reminder', f"Réservez la visite de votre logement : {listing['name']}",
                                  [host.email], {'first_name': host.first_name, 'listing': listing['name'],
                                                 'url': f"{settings.FRONTEND_URL}/hote/espace/visite"})
    if to_alert:
        cities = sorted({c['city'] for _, c in to_alert})
        hosts = users.comptes(c['host_id'] for _, c in to_alert)
        with transaction.atomic():
            VisitInvitationModel.objects.filter(pk__in=[i.pk for i, _ in to_alert]).update(alerted_at=now)
            services._envoyer(
                'hosts_without_appointment', f"[Kwa-Ba] Hôtes sans rendez-vous de visite ({len(to_alert)})",
                users.emails_actifs(['admin']), {
                    'listings': [{'name': c['name'], 'city': c['city'], 'host': _name(hosts.get(c['host_id'])),
                                  'phone': getattr(hosts.get(c['host_id']), 'phone', '') or '-',
                                  'invited_at': i.invited_at} for i, c in to_alert],
                    'cities_without_slot': [c for c in cities if not agenda.free_slots(c, 1)],
                    'url': f"{settings.FRONTEND_URL}/agent/agenda",
                })
    return {'host_reminders': len(to_remind), 'host_alerts': len(to_alert)}


def _listing_urls(listing_id) -> dict:
    return {'url_space': f"{settings.FRONTEND_URL}/hote/espace",
            'url_listing': f"{settings.FRONTEND_URL}/hebergements/{listing_id}"}


def _when(appointment) -> str:
    local = appointment.start.astimezone(ZoneInfo(agenda.DEFAULT_TIMEZONE))
    return f"{WEEKDAYS[local.weekday()]} {local.day}/{local.month:02d} à {local.hour} h{local.minute:02d}".replace(' h00', ' h')


def _close_mission(listing: dict, admin) -> None:
    if terrain.en_cours(MISSION_TYPE, str(listing['id'])):
        terrain.terminer(MISSION_TYPE, str(listing['id']), admin, decision='validee', titre=listing['name'],
                         sous_titre=listing['type_libelle'], ville=listing['city'])


@transaction.atomic
def validated_without_visit(listing: dict, admin, reason: str, keep_visit: bool) -> None:
    VisitInvitationModel.objects.filter(listing_id=listing['id']).delete()
    appointment, others_waiting = services.planned_visit(listing['id'])
    _close_mission(listing, admin)
    host = users.compte(listing['host_id'])
    visit = None
    if appointment:
        visit = {'when': _when(appointment), 'kept': keep_visit, 'shared': others_waiting}
        if keep_visit:
            agenda.keep_as_post_check(appointment.id)
        elif not others_waiting:
            agenda.cancel(appointment.id, author_id=admin.pk, by=agenda.BY_ADMIN, reason=reason, notify=False)
        agent = users.compte(appointment.agent_id)
        if agent:
            services._envoyer('validated_without_visit_agent',
                              f"[Kwa-Ba] Annonce validée sans visite : {listing['name']}", [agent.email], {
                                  'listing': listing['name'], 'city': listing['city'], 'reason': reason, **visit,
                                  'url': f"{settings.FRONTEND_URL}/agent/agenda/{appointment.id}",
                              })
    if host:
        services._envoyer('validated_without_visit_host', f"Votre logement est vérifié : {listing['name']}",
                          [host.email], {'first_name': host.first_name, 'listing': listing['name'], 'visit': visit,
                                         **_listing_urls(listing['id'])})


@transaction.atomic
def post_check(user, appointment_id, compliant: bool, reason: str):
    try:
        appointment = agenda.appointment(appointment_id)
    except agenda.AgendaError as exc:
        raise _from_agenda(exc) from None
    if not appointment.post_check or appointment.status != 'confirmed':
        raise AppointmentError("Ce rendez-vous n'est pas un contrôle a posteriori en cours.", 409)
    if appointment.agent_id != user.pk and user.role != 'admin':
        raise AppointmentError("Seul l'agent de cette visite ou un administrateur peut conclure le contrôle.", 403)
    reason = ' '.join(reason.split())
    if not compliant and len(reason) < 10:
        raise AppointmentError("Expliquez ce qui n'est pas conforme (10 caractères au moins) : l'hôte le recevra.")
    closing = 'Contrôle conforme' if compliant else f'Contrôle non conforme : {reason}'
    try:
        appointment = agenda.close(appointment.id, closing)
    except agenda.AgendaError as exc:
        raise _from_agenda(exc) from None
    if compliant:
        return appointment
    host = users.compte(appointment.requester_id)
    for target in appointment.targets:
        hebergements.enregistrer_verification(target.id, False, reason)
        if host:
            services._envoyer('annonce_refusee', f"Votre annonce n'est plus publiée : {target.title}", [host.email], {
                'prenom': host.first_name, 'hebergement': target.title, 'motif': reason,
                'url_espace': f"{settings.FRONTEND_URL}/hote/espace",
                'url_annonce': f"{settings.FRONTEND_URL}/hebergements/{target.id}",
            })
    services._envoyer('post_check_failed', f"[Kwa-Ba] Contrôle non conforme : {appointment.title}",
                      users.emails_actifs(['admin']), {
                          'title': appointment.title, 'city': appointment.city, 'reason': reason,
                          'agent': _name(users.compte(appointment.agent_id)),
                          'url': f"{settings.FRONTEND_URL}/backoffice/annonces?statut=refusee",
                      })
    return appointment
