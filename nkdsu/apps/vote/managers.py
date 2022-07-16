from __future__ import annotations

from typing import List, TYPE_CHECKING

from django.conf import settings
from django.db import models
from .utils import split_query_into_keywords

if TYPE_CHECKING:
    from .models import Note, Show, Track


class NoteQuerySet(models.QuerySet):
    def for_show_or_none(self, show: Show) -> models.QuerySet[Note]:
        return self.filter(models.Q(show=show) | models.Q(show=None))


class TrackQuerySet(models.QuerySet["Track"]):
    def _everything(self, show_secret_tracks: bool = False) -> TrackQuerySet:
        if show_secret_tracks:
            return self.all()
        else:
            return self.public()

    def for_decade(self, start_year: int) -> TrackQuerySet:
        return self.filter(year__gte=start_year, year__lt=start_year + 10)

    def public(self) -> TrackQuerySet:
        return self.filter(hidden=False, inudesu=False)

    def by_artist(self, artist: str, show_secret_tracks: bool = False) -> List[Track]:
        """
        Filters with Python, so does not return a queryset and is not lazy.
        """

        base_qs = self._everything(show_secret_tracks)
        qs = base_qs.filter(id3_artist__contains=artist).order_by('id3_title')
        return [t for t in qs if artist in t.artist_names()]

    def by_composer(self, composer: str, show_secret_tracks: bool = False) -> List[Track]:
        base_qs = self._everything(show_secret_tracks)
        qs = base_qs.filter(composer__contains=composer).order_by('id3_title')
        return [t for t in qs if composer in t.composer_names()]

    def by_anime(self, anime: str, show_secret_tracks: bool = False) -> List[Track]:
        """
        Behaves similarly to by_artist.
        """

        base_qs = self._everything(show_secret_tracks)
        qs = base_qs.filter(id3_title__contains=anime).order_by('id3_title')
        return [t for t in qs if t.has_anime(anime)]

    def search(self, query: str, show_secret_tracks: bool = False) -> TrackQuerySet:
        keywords = split_query_into_keywords(query)

        if len(keywords) == 0:
            return self.none()

        qs = self._everything(show_secret_tracks)

        for keyword in keywords:
            if (
                settings.DATABASES['default']['ENGINE'] ==
                'django.db.backends.postgresql'
            ):
                title_q = models.Q(id3_title__unaccent__icontains=keyword)
                artist_q = models.Q(id3_artist__unaccent__icontains=keyword)
            else:
                title_q = models.Q(id3_title__icontains=keyword)
                artist_q = models.Q(id3_artist__icontains=keyword)

            qs = qs.exclude(~title_q & ~artist_q)

        return qs
