from apps.finance.application.registre import ECRIVAINS
from apps.finance.application.service import GrandLivreService, RestitutionService
from apps.finance.infrastructure.clock import DjangoClock
from apps.finance.infrastructure.journal import AuditJournal
from apps.finance.infrastructure.notifications.alertes import EmailAlertes
from apps.finance.infrastructure.persistence.repositories import (DjangoGrandLivre, DjangoParametres,
                                                                  DjangoTransactionManager)
from apps.finance.infrastructure.persistence.restitutions import SqlRestitutions


def grand_livre_service() -> GrandLivreService:
    return GrandLivreService(grand_livre=DjangoGrandLivre(), parametres=DjangoParametres(), alertes=EmailAlertes(),
                             journal=AuditJournal(), tx=DjangoTransactionManager(), clock=DjangoClock())


def restitution_service() -> RestitutionService:
    return RestitutionService(restitutions=SqlRestitutions(), ecrivains=ECRIVAINS)
