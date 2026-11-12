from rest_framework.response import Response

from apps.agenda.domain.settings import BOUNDS, AgendaSettings, InvalidSettings
from apps.agenda.infrastructure.container import agenda_service
from apps.securite.audit import journaliser
from apps.securite.backoffice import VueAdmin
from apps.securite.permissions import has_special_permission
from apps.users import api as users

PERMISSION = 'agenda_settings'


def _settings_json(stored) -> dict:
    author = users.compte(stored.updated_by_id) if stored.updated_by_id else None
    return {
        'values': stored.values.as_dict(),
        'defaults': AgendaSettings().as_dict(),
        'bounds': {name: {'min': low, 'max': high} for name, (low, high) in BOUNDS.items()},
        'updated_at': stored.updated_at,
        'updated_by': (author.get_full_name() or author.email) if author else None,
    }


class AgendaSettingsView(VueAdmin):
    def check_permissions(self, request):
        super().check_permissions(request)
        if not has_special_permission(request.user, PERMISSION):
            self.permission_denied(request, message="Les réglages de l'agenda ne vous sont pas ouverts.")

    def get(self, request):
        return Response(_settings_json(agenda_service().stored_settings()))

    def put(self, request):
        changes = request.data if isinstance(request.data, dict) else {}
        try:
            before, stored = agenda_service().update_settings(changes, request.user.pk)
        except InvalidSettings as exc:
            return Response({'detail': str(exc), 'errors': exc.errors}, status=400)
        after = stored.values.as_dict()
        diff = {name: {'before': value, 'after': after[name]} for name, value in before.as_dict().items()
                if after[name] != value}
        if diff:
            journaliser('agenda_settings_changed', request, utilisateur=request.user, changes=diff)
        return Response(_settings_json(stored))
