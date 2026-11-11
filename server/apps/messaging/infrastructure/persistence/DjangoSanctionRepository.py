import datetime
import uuid
from typing import List, Optional

from apps.messaging.domain.entities.Sanction import Sanction
from apps.messaging.domain.repositories.SanctionRepository import SanctionRepository
from apps.messaging.domain.services.SanctionLadder import ADMIN_DECISION, SUSPENSIONS, AppliedSuspension
from apps.messaging.infrastructure.persistence.models import SanctionModel

FIELDS = ('user_id', 'report_id', 'step', 'category', 'created_at', 'starts_at', 'ends_at', 'cancelled_at',
          'contested_at', 'contest_text', 'contest_status', 'contest_reviewed_at', 'contest_reviewed_by_id',
          'contest_note')


class DjangoSanctionRepository(SanctionRepository):

    def _to_entity(self, model: SanctionModel) -> Sanction:
        return Sanction(id=model.id, **{f: getattr(model, f) for f in FIELDS})

    def add(self, sanction: Sanction) -> Sanction:
        return self._to_entity(SanctionModel.objects.create(**{f: getattr(sanction, f) for f in FIELDS}))

    def get(self, sanction_id: int) -> Optional[Sanction]:
        model = SanctionModel.objects.filter(pk=sanction_id).first()
        return self._to_entity(model) if model else None

    def save(self, sanction: Sanction) -> None:
        SanctionModel.objects.filter(pk=sanction.id).update(**{f: getattr(sanction, f) for f in FIELDS})

    def for_report(self, report_id: int) -> List[Sanction]:
        return [self._to_entity(m) for m in SanctionModel.objects.filter(report_id=report_id)]

    def for_user(self, user_id: uuid.UUID, limit: int) -> List[Sanction]:
        return [self._to_entity(m) for m in SanctionModel.objects.filter(user_id=user_id).order_by('-created_at')[:limit]]

    def applied_suspensions(self, user_id: uuid.UUID) -> List[AppliedSuspension]:
        rows = SanctionModel.objects.filter(user_id=user_id, step__in=SUSPENSIONS, cancelled_at__isnull=True)
        return [AppliedSuspension(m.step, m.starts_at, m.ends_at) for m in rows.order_by('starts_at')]

    def admin_decision_count(self, user_id: uuid.UUID) -> int:
        return SanctionModel.objects.filter(user_id=user_id, step=ADMIN_DECISION, cancelled_at__isnull=True).count()

    def active_suspension_end(self, user_id: uuid.UUID, now: datetime.datetime) -> Optional[datetime.datetime]:
        return (SanctionModel.objects
                .filter(user_id=user_id, step__in=SUSPENSIONS, cancelled_at__isnull=True,
                        starts_at__lte=now, ends_at__gt=now)
                .order_by('-ends_at').values_list('ends_at', flat=True).first())
