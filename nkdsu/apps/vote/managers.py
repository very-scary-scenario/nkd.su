from django.db import models
from .utils import split_query_into_keywords


class NoteManager(models.Manager):
    def for_show_or_none(self, show):
        return self.filter(models.Q(show=show) | models.Q(show=None))


class TrackManager(models.Manager):
    def _everything(self, show_secret_tracks=False):
        if show_secret_tracks:
            return self.all()
        else:
            return self.public()

    def public(self):
        return self.filter(hidden=False, inudesu=False)

    def by_artist(self, artist, show_secret_tracks=False):
        """
        Filters with Python, so does not return a queryset and is not lazy.
        """

        base_qs = self._everything(show_secret_tracks)
        qs = base_qs.filter(id3_artist__contains=artist).order_by('id3_title')
        return [t for t in qs if artist in t.artist_names()]

    def by_anime(self, anime, show_secret_tracks=False):
        """
        Behaves similarly to by_artist.
        """

        base_qs = self._everything(show_secret_tracks)
        qs = base_qs.filter(id3_title__contains=anime).order_by('id3_title')
        return [t for t in qs if t.role_detail.get('anime') == anime]

    def search(self, query, show_secret_tracks=False):
        keywords = split_query_into_keywords(query)

        if len(keywords) == 0:
            return []

        qs = self._everything(show_secret_tracks)

        for keyword in keywords:
            qs = qs.exclude(~models.Q(
                id3_title__icontains=keyword,
            ) & ~models.Q(
                id3_artist__icontains=keyword,
            ))

        return qs
