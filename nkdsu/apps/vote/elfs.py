from django.contrib.auth.models import AnonymousUser, User


ELFS_NAME = "Elfs"


def is_elf(user: User | AnonymousUser) -> bool:
    return user.is_authenticated and (
        user.is_staff or user.groups.filter(name=ELFS_NAME).exists()
    )
