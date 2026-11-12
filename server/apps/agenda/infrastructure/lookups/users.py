from apps.agenda.application.ports import PeopleLookup, Person
from apps.users import api as users


def _person(account) -> Person:
    return Person(id=account.id, name=account.get_full_name() or account.email, email=account.email,
                  active_agent=account.is_active and account.role in ('agent', 'admin'))


class DjangoPeopleLookup(PeopleLookup):
    def person(self, user_id):
        account = users.compte(user_id)
        return _person(account) if account else None

    def people(self, user_ids):
        return {i: _person(a) for i, a in users.comptes(user_ids).items()}

    def active_agents(self):
        return users.ids_actifs(['agent'])

    def admin_emails(self):
        return users.emails_actifs(['admin'])
