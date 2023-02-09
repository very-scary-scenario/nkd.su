from typing import Optional, Sequence

from django.apps import AppConfig
from django.db.models import Model
from django.db.models.signals import post_save


class VoteConfig(AppConfig):
    name = 'nkdsu.apps.vote'

    def ready(self) -> None:
        from .models import Profile
        from django.contrib.auth import get_user_model

        User = get_user_model()

        def create_profile_on_user_creation(
            sender: type[Model],
            instance: Model,
            created: bool,
            raw: bool,
            using: Optional[str],
            update_fields: Optional[Sequence[str]],
            **kwargs,
        ) -> None:

            if created and (not raw) and isinstance(instance, User):
                Profile.objects.create(user=instance)

        post_save.connect(create_profile_on_user_creation)
