#!/usr/bin/env python

from models import Track
from django.utils.timezone import utc, make_aware


def update_library(tree, dry_run=False, inudesu=False):
    changes = []
    alltracks = Track.objects.filter(inudesu=inudesu)
    tracks_kept = []

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
                    or (db_track.composer != t['Composer'])
                    or (db_track.added != added)):
                # we need to update an existing track
                changed = True
                pre_change = unicode(db_track)

        if new or changed:
            db_track.id = t['Persistent ID']
            db_track.id3_title = t['Name']
            db_track.id3_artist = t['Artist']
            db_track.id3_album = t['Album']
            db_track.msec = t['Total Time']
            db_track.msec = t['Total Time']
            db_track.added = added
            db_track.inudesu = inudesu

        if new:
            if not inudesu:
                db_track.hidden = True
            else:
                db_track.hidden = False

            changes.append('new:\n%s' % unicode(db_track))

        if changed:
            changes.append('change:\n%s' % pre_change)
            changes.append('to:\n%s' % unicode(db_track))

        if (new or changed) and (not dry_run):
            db_track.save()

        tracks_kept.append(db_track)

    for track in [t for t in alltracks
                  if t not in tracks_kept and not t.hidden]:
        changes.append('hide:\n%s' % unicode(track))
        if not dry_run:
            track.hidden = True
            track.save()

    return changes
