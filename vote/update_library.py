#!/usr/bin/env python

from django.core.management.base import BaseCommand, CommandError
import plistlib
from models import Track
from time import strptime
from django.utils.timezone import utc, make_aware

def update_library(plist, dry_run=False):
    changes = []
    alltracks = Track.objects.all()
    tracks_kept = []

    tree = plistlib.readPlist(plist)

    for tid in tree['Tracks']:
        changed = False
        new = False

        t = tree['Tracks'][tid]
        added = make_aware(t['Date Added'], utc)

        if 'Album' not in t:
            t['Album'] = '' # to prevent future KeyErrors

        try:
            db_track = Track.objects.get(id=t['Persistent ID'])
        except Track.DoesNotExist:
            # we need to make a new track
            new = True
            db_track = Track()

        else:
            if (db_track.id3_title != t['Name']) or (db_track.id3_artist != t['Artist']) or (db_track.id3_album != t['Album']) or (db_track.msec != t['Total Time']) or (db_track.added != added):
                # we need to update an existing track
                changed = True
                pre_change = db_track.canonical_string()

        if new or changed:
            db_track.id = t['Persistent ID']
            db_track.id3_title = t['Name']
            db_track.id3_artist = t['Artist']
            db_track.id3_album = t['Album']
            db_track.msec = t['Total Time']
            db_track.added = added

        if new:
            db_track.hidden = True
            changes.append('new: %s' % (db_track.canonical_string()))

        if changed:
            changes.append('change: %s' % pre_change)
            changes.append('to: %s' % db_track.canonical_string())

        if (new or changed) and (not dry_run):
            db_track.save()

        tracks_kept.append(db_track)

    for track in [t for t in Track.objects.all() if t not in tracks_kept and not t.hidden]:
        changes.append('hide: %s' % track.canonical_string())
        if not dry_run:
            track.hidden = True
            track.save()

    return changes

