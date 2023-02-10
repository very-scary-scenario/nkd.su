from typing import Optional, Sequence

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db.models import Model

from .elfs import ELFS_NAME
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


def make_elfs(**kwargs) -> None:
    Group.objects.get_or_create(name=ELFS_NAME)
