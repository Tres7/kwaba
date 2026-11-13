"""Super admins (the directors) are managed here only, never through the API: a stolen account cannot create one."""
from django.core.management.base import BaseCommand, CommandError

from apps.activity import api as activity
from apps.users.infrastructure.persistence.models import UserModel


class Command(BaseCommand):
    help = "Gives (or removes, with --retirer) the super admin rights of an existing account."

    def add_arguments(self, parser):
        parser.add_argument('email')
        parser.add_argument('--retirer', action='store_true')

    def handle(self, *args, email, retirer, **options):
        compte = UserModel.objects.filter(email__iexact=email).first()
        if not compte:
            raise CommandError(f"Aucun compte pour {email}.")
        if retirer:
            if not UserModel.objects.filter(is_superuser=True, is_active=True).exclude(pk=compte.pk).exists():
                raise CommandError("C'est le dernier super administrateur : le retirer bloquerait la gestion des admins.")
            compte.is_superuser = compte.is_staff = False
        else:
            compte.is_superuser = compte.is_staff = True
            compte.role = 'admin'
            compte.admin_sections = compte.admin_expire_le = None
            compte.role_avant_admin = ''
        compte.save(update_fields=['is_superuser', 'is_staff', 'role', 'admin_sections', 'admin_expire_le', 'role_avant_admin'])
        activity.record('super_admin_retire' if retirer else 'super_admin_nomme',
                        target=activity.Target('account', str(compte.pk), compte.email))
        self.stdout.write(f"{compte.email} : super administrateur {'retiré' if retirer else 'nommé'}.")
