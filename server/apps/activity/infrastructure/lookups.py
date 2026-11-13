from django.contrib.auth import get_user_model
from django.db.models import Q

from apps.activity.application.ports import PeopleLookup, Person


class DjangoPeopleLookup(PeopleLookup):
    def people(self, ids):
        ids = [i for i in ids if i]
        if not ids:
            return {}
        accounts = get_user_model().objects.filter(pk__in=ids).only('id', 'email', 'first_name', 'last_name', 'role')
        return {a.pk: Person(id=a.pk, name=f'{a.first_name} {a.last_name}'.strip() or a.email, email=a.email,
                             role=a.role) for a in accounts}

    def matching(self, text):
        return list(get_user_model().objects.filter(
            Q(email__icontains=text) | Q(first_name__icontains=text) | Q(last_name__icontains=text)
            | Q(phone__icontains=text)).values_list('id', flat=True)[:200])
