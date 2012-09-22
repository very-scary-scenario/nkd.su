#!/usr/bin/env python

from vote.models import Track, Vote

import plistlib
from pprint import pprint

tree = plistlib.readPlist('songlibrary.xml')

for track in Track.objects.all():
    track.delete()

# Vote.objects.all().delete() # ids may change

for tid in tree['Tracks']:
    t = tree['Tracks'][tid]
    print t
    track = Track(id3_title=t['Name'], id3_artist=t['Artist'], id=t['Persistent ID'])

    try:
        track.id3_album = t['Album']
    except KeyError:
        pass

    track.save()
