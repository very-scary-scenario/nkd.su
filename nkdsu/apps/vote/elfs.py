from django.contrib.auth.models import AnonymousUser, Group, User


ELFS_NAME = "Elfs"


def _get_elfs() -> Group:
    elfs, _ = Group.objects.get_or_create(name=ELFS_NAME)
    return elfs


def is_elf(user: User | AnonymousUser) -> bool:
    return user.is_authenticated and (
        user.is_staff or user.groups.filter(name=ELFS_NAME).exists()
    )


_get_elfs()
