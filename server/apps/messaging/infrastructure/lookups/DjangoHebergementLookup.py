import uuid
from typing import Dict, List, Optional

from apps.hebergements import api as hebergements
from apps.messaging.application.ports.HebergementLookup import HebergementInfo, HebergementLookup


class DjangoHebergementLookup(HebergementLookup):
    """Only contact point of messaging with the listings module."""

    def _to_info(self, h: dict) -> HebergementInfo:
        return HebergementInfo(
            id=h['id'], name=h['name'], host_id=h['host_id'],
            city=h['city'], image_url=h['image_url'] or '',
        )

    def get(self, hebergement_id: uuid.UUID) -> Optional[HebergementInfo]:
        return self.get_many([hebergement_id]).get(hebergement_id)

    def get_many(self, hebergement_ids: List[uuid.UUID]) -> Dict[uuid.UUID, HebergementInfo]:
        return {id_: self._to_info(h) for id_, h in hebergements.resumes(hebergement_ids).items()}

    def is_published(self, hebergement_id: uuid.UUID) -> bool:
        return hebergements.est_publiee(hebergement_id)
