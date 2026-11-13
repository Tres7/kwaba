from apps.activity.domain.entities import Target
from apps.activity.infrastructure.container import activity_service
from apps.securite.limites import ip_client

__all__ = ['Target', 'hold', 'record']


def record(action: str, request=None, *, actor=None, email: str = '', target: Target | None = None, **details) -> None:
    activity_service().record(action, actor=actor, actor_email=email, target=target, details=details,
                              ip=ip_client(request) if request is not None else None)


def hold(target_kind: str, target_id, on: bool) -> None:
    activity_service().hold(target_kind, str(target_id), on)
