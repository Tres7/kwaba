from abc import ABC, abstractmethod
from datetime import date


class NotificationSender(ABC):

    @abstractmethod
    def send_verification_email(self, to: str, first_name: str, code: str) -> None:
        pass

    @abstractmethod
    def send_welcome_email(self, to: str, first_name: str) -> None:
        pass

    @abstractmethod
    def send_new_message_email(
        self, to: str, first_name: str, sender_first_name: str,
        hebergement_name: str, message_preview: str, conversation_url: str,
    ) -> None:
        pass

    @abstractmethod
    def send_password_reset_email(self, to: str, first_name: str, code: str) -> None:
        pass

    @abstractmethod
    def send_booking_cancelled_listing_removed_email(
        self, to: str, first_name: str, hebergement_name: str, city: str, check_in: date, check_out: date,
    ) -> None:
        pass
