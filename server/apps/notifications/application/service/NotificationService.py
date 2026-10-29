from datetime import date

from apps.notifications.application.ports.NotificationSender import NotificationSender


class NotificationService:

    def __init__(self, sender: NotificationSender):
        self._sender = sender

    def send_verification_email(self, to: str, first_name: str, code: str) -> None:
        self._sender.send_verification_email(to, first_name, code)
    
    def send_welcome_email(self, to: str, first_name: str) -> None:
        self._sender.send_welcome_email(to, first_name)

    def send_new_message_email(
        self, to: str, first_name: str, sender_first_name: str,
        hebergement_name: str, message_preview: str, conversation_url: str,
    ) -> None:
        self._sender.send_new_message_email(
            to, first_name, sender_first_name, hebergement_name, message_preview, conversation_url,
        )

    def send_password_reset_email(self, to: str, first_name: str, code: str) -> None:
        self._sender.send_password_reset_email(to, first_name, code)

    def send_booking_cancelled_listing_removed_email(
        self, to: str, first_name: str, hebergement_name: str, city: str, check_in: date, check_out: date,
    ) -> None:
        self._sender.send_booking_cancelled_listing_removed_email(
            to, first_name, hebergement_name, city, check_in, check_out,
        )
