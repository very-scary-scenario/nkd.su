#!/usr/bin/env python

import plistlib
from models import Track
from django.utils.timezone import utc, make_aware


def update_library(plist, dry_run=False, is_inudesu=False):
    changes = []
    alltracks = Track.objects.filter(inudesu=is_inudesu)
    tracks_kept = []

    tree = plistlib.readPlist(plist)

    for tid in tree['Tracks']:
        changed = False
        new = False

        t = tree['Tracks'][tid]
        added = make_aware(t['Date Added'], utc)

        if 'Album' not in t:
            t['Album'] = ''  # to prevent future KeyErrors

        try:
            db_track = Track.objects.get(id=t['Persistent ID'])
        except Track.DoesNotExist:
            # we need to make a new track
            new = True
            db_track = Track()

        else:
            if ((db_track.id3_title != t['Name'])
                    or (db_track.id3_artist != t['Artist'])
                    or (db_track.id3_album != t['Album'])
                    or (db_track.msec != t['Total Time'])
                    or (db_track.added != added)):
                # we need to update an existing track
                changed = True
                pre_change = db_track.deets()

        if new or changed:
            db_track.id = t['Persistent ID']
            db_track.id3_title = t['Name']
            db_track.id3_artist = t['Artist']
            db_track.id3_album = t['Album']
            db_track.msec = t['Total Time']
            db_track.added = added
            db_track.inudesu = is_inudesu

        if new:
            if not is_inudesu:
                db_track.hidden = True
            else:
                db_track.hidden = False

            changes.append('new:\n%s' % (db_track.deets()))

        if changed:
            changes.append('change:\n%s' % pre_change)
            changes.append('to:\n%s' % db_track.deets())

        if (new or changed) and (not dry_run):
            db_track.save()

        tracks_kept.append(db_track)

    for track in [t for t in alltracks
                  if t not in tracks_kept and not t.hidden]:
        changes.append('hide:\n%s' % track.deets())
        if not dry_run:
            track.hidden = True
            track.save()

    return changes
