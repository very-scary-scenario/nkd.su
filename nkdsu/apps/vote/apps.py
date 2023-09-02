from django.apps import AppConfig
from django.db.models.signals import post_migrate, post_save


class VoteConfig(AppConfig):
    name = 'nkdsu.apps.vote'

    def ready(self) -> None:
        from . import signals

        post_save.connect(signals.create_profile_on_user_creation)
        post_migrate.connect(signals.make_elfs)
