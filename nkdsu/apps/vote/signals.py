from typing import Optional, Sequence

from django.contrib.auth import get_user_model
from django.db.models import Model

from .models import Profile

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
