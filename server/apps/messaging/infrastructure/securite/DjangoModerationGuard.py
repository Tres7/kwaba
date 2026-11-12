import uuid

from apps.messaging.application.ports.ModerationGuard import ModerationGuard, ModerationVerdict
from apps.securite import fraude, moderation


class DjangoModerationGuard(ModerationGuard):

    def mode(self) -> str:
        return moderation.mode()

    def screen(self, text: str) -> ModerationVerdict:
        result = moderation.analyze(text)
        return ModerationVerdict(result.level, result.categories)

    def record(self, user_id: uuid.UUID, conversation_id: uuid.UUID, kind: str, verdict: ModerationVerdict,
               content: str) -> None:
        fraude.record_moderation(user_id, conversation_id, kind, verdict.categories, verdict.level,
                                 moderation.excerpt(content))

    def record_false_positive(self, user_id: uuid.UUID, conversation_id: uuid.UUID, verdict: ModerationVerdict,
                              content: str) -> None:
        fraude.record_moderation(user_id, conversation_id, 'false_positive', verdict.categories, verdict.level,
                                 moderation.excerpt(content))
