from django.apps import AppConfig


class MessagingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.messaging'
    # 'messages' is already taken by django.contrib.messages
    label = 'messaging'
