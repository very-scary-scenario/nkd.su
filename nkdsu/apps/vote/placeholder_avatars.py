from typing import Optional

from django.contrib.staticfiles import finders

from .voter import Voter


__all__ = ['placeholder_avatar_for']


def placeholder_avatar_for(voter: Voter) -> str:
    uid: tuple[str, Optional[int], Optional[int]] = ('nkdsu-voter',) + voter.voter_id

    return _static_path_from_filename(
        AVATAR_FILENAMES[hash(uid) % len(AVATAR_FILENAMES)]
    )


AVATAR_FILENAMES = [
    f'icon{i}-{deg}.svg' for i in range(1, 5) for deg in range(0, 360, 15)
]


def _static_path_from_filename(avatar_filename: str) -> str:
    return f'i/placeholder-avatars/{avatar_filename}'


def _verify_avatar_list() -> None:
    """
    Make sure all the avatars are actually present.
    """

    for avatar_filename in AVATAR_FILENAMES:
        if finders.find(_static_path_from_filename(avatar_filename)) is None:
            raise AssertionError(f'{avatar_filename} placeholder avatar not present')


_verify_avatar_list()
