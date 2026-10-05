from django.apps import AppConfig
from django.db.models.signals import post_migrate


class NewsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'news'

    def ready(self):
        """Import signal handlers and create role groups after migrate."""
        from . import signals

        post_migrate.connect(signals.create_role_groups, sender=self)
