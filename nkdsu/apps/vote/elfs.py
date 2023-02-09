from django.contrib.auth.models import Group


def _prepare_elfs() -> Group:
    elfs, _ = Group.objects.get_or_create(name="Elfs")
    return elfs


ELFS: Group = _prepare_elfs()
