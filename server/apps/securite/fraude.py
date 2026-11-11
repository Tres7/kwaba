"""Anti-fraud alerts: every bypass attempt is recorded for an administrator.

At the SEUIL-th report of the same account over 30 days, the administrators are notified by email (once).
"""
import logging
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from .coordonnees import Trouvaille, masquees
from .models import AlerteFraudeModel

logger = logging.getLogger('apps.securite')

SEUIL = 3
FENETRE = timedelta(days=30)


def signaler(utilisateur_id, contexte: str, objet_id, trouvailles: list[Trouvaille]) -> AlerteFraudeModel | None:
    if not trouvailles:
        return None
    alerte = AlerteFraudeModel.objects.create(
        utilisateur_id=utilisateur_id, contexte=contexte, objet_id=str(objet_id),
        types=sorted({t.type for t in trouvailles}), extraits=[t.valeur[:120] for t in trouvailles][:10],
        masquee=masquees(trouvailles),
    )
    nombre = AlerteFraudeModel.objects.filter(utilisateur_id=utilisateur_id, kind='bypass',
                                              cree_le__gte=timezone.now() - FENETRE).count()
    if nombre == SEUIL:
        transaction.on_commit(lambda: _prevenir_admins(alerte, nombre))
    return alerte


def _prevenir_admins(alerte: AlerteFraudeModel, nombre: int) -> None:
    from apps.notifications.api import send_mail

    try:
        u = get_user_model().objects.get(pk=alerte.utilisateur_id)
        admins = list(get_user_model().objects.filter(role='admin', is_active=True).values_list('email', flat=True)[:10])
        if not admins:
            return
        message = (
            f"{nombre} tentatives de contournement en 30 jours pour {u.first_name} {u.last_name} <{u.email}> ({u.get_role_display()}).\n\n"
            f"Dernière : {alerte.get_contexte_display().lower()}, {', '.join(alerte.types)}.\n\n"
            f"Examinez-les dans le back-office : {settings.FRONTEND_URL.rstrip('/')}/backoffice/anti-fraude\n"
        )
        send_mail(f"[Kwa-Ba] Anti-fraude : {u.email}", message, settings.DEFAULT_FROM_EMAIL, admins)
    except Exception:
        logger.exception("Alerte anti-fraude non envoyée")


MODERATION_KINDS = ('refusal', 'simulated', 'warning_ignored', 'false_positive')
EXCERPT_KINDS = MODERATION_KINDS + ('report', 'contest')
THREAT = 'threat'
THREAT_EMAIL_PERIOD = timedelta(hours=1)


def _moderation_settings() -> dict:
    return settings.MODERATION


def _backoffice_link() -> str:
    return f"{settings.FRONTEND_URL.rstrip('/')}/backoffice/anti-fraude"


def _describe(user_id) -> str:
    user = get_user_model().objects.filter(pk=user_id).first()
    if not user:
        return str(user_id)
    return f"{user.first_name} {user.last_name} <{user.email}> ({user.get_role_display()})".strip()


def _mail_admins(subject: str, body: str) -> None:
    from apps.notifications.api import send_mail

    try:
        admins = list(get_user_model().objects.filter(role='admin', is_active=True).values_list('email', flat=True)[:10])
        if admins:
            send_mail(f"[Kwa-Ba] {subject}", body, settings.DEFAULT_FROM_EMAIL, admins)
    except Exception:
        logger.exception("Alerte de modération non envoyée")


def _create(user_id, kind: str, object_id, types, excerpts=(), level: str = '', treated: bool = False):
    now = timezone.now()
    return AlerteFraudeModel.objects.create(
        utilisateur_id=user_id, contexte='message', objet_id=str(object_id), kind=kind, types=list(types),
        extraits=[e for e in excerpts if e][:10], level=level, traitee=treated, traitee_le=now if treated else None,
    )


def record_moderation(user_id, conversation_id, kind: str, categories, level: str, excerpt: str) -> AlerteFraudeModel:
    alert = _create(user_id, kind, conversation_id, categories, [excerpt], level)
    if THREAT in categories and kind != 'false_positive':
        transaction.on_commit(lambda: alert_threats(user_id))
    if kind == 'refusal':
        window = timedelta(days=_moderation_settings()['WINDOW_DAYS'])
        refusals = AlerteFraudeModel.objects.filter(utilisateur_id=user_id, kind='refusal',
                                                    cree_le__gte=timezone.now() - window).count()
        if refusals == _moderation_settings()['REFUSAL_ALERT_THRESHOLD']:
            transaction.on_commit(lambda: _mail_admins(
                f"Modération : {refusals} messages refusés",
                f"{refusals} messages refusés en {window.days} jours pour {_describe(user_id)}.\n\n"
                f"Examinez-les dans le back-office : {_backoffice_link()}\n",
            ))
    return alert


def record_report(author_id, report_id, reason: str, excerpt: str) -> AlerteFraudeModel:
    alert = _create(author_id, 'report', report_id, [reason], [excerpt])
    if reason == THREAT:
        transaction.on_commit(lambda: alert_threats(author_id))
    return alert


def record_sanction(user_id, sanction_id, step: str, needs_decision: bool) -> AlerteFraudeModel:
    alert = _create(user_id, 'sanction', sanction_id, [step], treated=not needs_decision)
    if needs_decision:
        transaction.on_commit(lambda: _mail_admins(
            "Modération : décision à prendre",
            f"Nouveau signalement confirmé après une suspension de 7 jours pour {_describe(user_id)}.\n"
            f"Une suspension du compte est à décider.\n\n{_backoffice_link()}\n",
        ))
    return alert


def record_contest(user_id, sanction_id, text: str) -> AlerteFraudeModel:
    return _create(user_id, 'contest', sanction_id, ['contest'], [text[:120]])


def record_abusive_reporter(reporter_id, rejected_count: int) -> AlerteFraudeModel:
    alert = _create(reporter_id, 'abusive_reporter', reporter_id, ['abusive_reporter'])
    window = _moderation_settings()['WINDOW_DAYS']
    transaction.on_commit(lambda: _mail_admins(
        "Modération : signalements rejetés",
        f"{rejected_count} signalements rejetés en {window} jours pour {_describe(reporter_id)}.\n"
        f"Aucune sanction automatique : jugez s'il s'agit de signalements abusifs.\n\n{_backoffice_link()}\n",
    ))
    return alert


def close(kind: str, object_id, admin_id, note: str = '') -> None:
    AlerteFraudeModel.objects.filter(kind=kind, objet_id=str(object_id), traitee=False).update(
        traitee=True, traitee_le=timezone.now(), traitee_par_id=admin_id, note=(note or '')[:1000])


def alert_threats(user_id) -> None:
    from .limites import incrementer

    try:
        sent, _ = incrementer(f'moderation-threat-email:{user_id}', int(THREAT_EMAIL_PERIOD.total_seconds()))
        if sent > 1:
            return
        pending = list(AlerteFraudeModel.objects.filter(
            utilisateur_id=user_id, types__contains=[THREAT], threat_notified_at__isnull=True,
        ).exclude(kind='false_positive').order_by('cree_le'))
        if not pending:
            return
        lines = '\n'.join(f"- {a.cree_le:%d/%m/%Y %H:%M} : {a.get_kind_display().lower()}" for a in pending)
        _mail_admins(
            f"Menace détectée : {_describe(user_id)}",
            f"Menace(s) détectée(s) dans la messagerie pour {_describe(user_id)} :\n{lines}\n\n"
            f"Examinez-les sans attendre dans le back-office : {_backoffice_link()}\n",
        )
        AlerteFraudeModel.objects.filter(pk__in=[a.pk for a in pending]).update(threat_notified_at=timezone.now())
    except Exception:
        logger.exception("Alerte de menace non envoyée")


def flush_threat_alerts() -> int:
    cutoff = timezone.now() - THREAT_EMAIL_PERIOD
    users = set(AlerteFraudeModel.objects.filter(
        types__contains=[THREAT], threat_notified_at__isnull=True, cree_le__lt=cutoff,
    ).exclude(kind='false_positive').values_list('utilisateur_id', flat=True))
    for user_id in users:
        alert_threats(user_id)
    return len(users)


def set_legal_hold(kind: str, object_id, hold: bool) -> None:
    AlerteFraudeModel.objects.filter(kind=kind, objet_id=str(object_id)).update(legal_hold=hold)


def purge_moderation_excerpts(now=None) -> int:
    cutoff = (now or timezone.now()) - timedelta(days=_moderation_settings()['REFUSAL_EXCERPT_RETENTION_DAYS'])
    return (AlerteFraudeModel.objects.filter(kind__in=EXCERPT_KINDS, cree_le__lt=cutoff, legal_hold=False)
            .exclude(extraits=[]).update(extraits=[]))
