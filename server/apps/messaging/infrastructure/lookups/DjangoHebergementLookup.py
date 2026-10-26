import uuid
from typing import Dict, List, Optional

from apps.hebergements.models import HebergementModel
from apps.messaging.application.ports.HebergementLookup import HebergementInfo, HebergementLookup


class DjangoHebergementLookup(HebergementLookup):
    """Only contact point of messaging with the model of the listings module."""

    FIELDS = ('id', 'name', 'host_id', 'city', 'image_url')

    def _to_info(self, row: dict) -> HebergementInfo:
        return HebergementInfo(
            id=row['id'], name=row['name'], host_id=row['host_id'],
            city=row['city'], image_url=row['image_url'] or '',
        )

    def get(self, hebergement_id: uuid.UUID) -> Optional[HebergementInfo]:
        row = HebergementModel.objects.filter(id=hebergement_id).values(*self.FIELDS).first()
        return self._to_info(row) if row else None

    def get_many(self, hebergement_ids: List[uuid.UUID]) -> Dict[uuid.UUID, HebergementInfo]:
        rows = HebergementModel.objects.filter(id__in=hebergement_ids).values(*self.FIELDS)
        return {row['id']: self._to_info(row) for row in rows}
