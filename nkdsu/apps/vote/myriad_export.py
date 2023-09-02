"""
Tools for interacting with CSV exports of the library from Myriad Playout.
"""

from csv import DictReader
from dataclasses import dataclass
from typing import Callable, Iterable, Optional

from .models import Track


def has_hook(entry: dict[str, str]) -> bool:
    match entry['HasHook']:
        case 'YES':
            return True
        case '':
            return False

    raise ValueError(f'could not recognise HasHook entry {entry["HasHook"]!r}')


@dataclass
class PlayoutEntry:
    item_type: str
    media_id: int
    title: str
    artists: str
    has_hook: bool

    @classmethod
    def from_csv(cls, entry: dict[str, str]) -> 'PlayoutEntry':
        return cls(
            item_type=entry['ItemType'],
            media_id=int(entry['MediaId']),
            title=entry['Title'],
            artists=entry['Artists'],
            has_hook=has_hook(entry),
        )

    def matched_track(self) -> Optional[Track]:
        """
        Return the :class:`.Track` that matches this entry, if applicable.
        """

        def pass_if_none_exists(get_track=Callable[[], Track]) -> Optional[Track]:
            try:
                return get_track()
            except Track.DoesNotExist:
                return None

        return (
            pass_if_none_exists(lambda: Track.objects.get(media_id=self.media_id))
            or pass_if_none_exists(
                lambda: Track.objects.get(
                    revealed__isnull=False,
                    hidden=False,
                    id3_title=self.title,
                    id3_artist__startswith=self.artists,
                )
            )
            or None
        )

    def update_matched_track(self) -> bool:
        """
        Update and save the :class:`.Track` we're able to match against this entry.

        :returns: :data:`True` if we matched against something and updated it, otherwise :data:`False`.
        """

        matched_track = self.matched_track()
        if matched_track is None:
            return False

        matched_track.media_id = self.media_id
        matched_track.has_hook = self.has_hook

        matched_track.save()

        return True


def entries_for_file(file: Iterable[str]) -> Iterable[PlayoutEntry]:
    reader = DictReader(file)
    for csv_entry in reader:
        yield PlayoutEntry.from_csv(csv_entry)
