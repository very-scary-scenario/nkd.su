from django.db import models
from .utils import split_query_into_keywords


class NoteManager(models.Manager):
    def for_show_or_none(self, show):
        return self.filter(models.Q(show=show) | models.Q(show=None))


class TrackManager(models.Manager):
    def public(self):
        return self.filter(hidden=False, inudesu=False)

    def search(self, query, show_secret_tracks=False):
        keywords = split_query_into_keywords(query)

        if len(keywords) == 0:
            return []

        if show_secret_tracks:
            qs = self.all()
        else:
            qs = self.public()

        for keyword in keywords:
            qs = qs.exclude(~models.Q(id3_title__icontains=keyword) &
                            ~models.Q(id3_artist__icontains=keyword))

        return qs
