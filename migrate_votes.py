import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nekodesu.settings")

from vote.models import Vote

from django.conf import settings

""" Migrate votes from Vote.track to the new Vote.tracks """
for vote in Vote.objects.all():
    vote.tracks = [vote.track]
    vote.track = None
    print vote.tracks
    print vote.track
    vote.save()

