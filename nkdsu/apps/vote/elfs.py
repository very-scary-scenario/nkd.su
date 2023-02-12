from django.contrib.auth.models import AnonymousUser, User


#: The of the group that elfs belong to
ELFS_NAME = "Elfs"


def is_elf(user: User | AnonymousUser) -> bool:
    """
    Return :data:`True` if ``user`` is an elf.
    """

    return user.is_authenticated and (
        user.is_staff or user.groups.filter(name=ELFS_NAME).exists()
    )
