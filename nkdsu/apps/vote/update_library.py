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
            db_dict = {
                'title': db_track.id3_title,
                'artist': db_track.id3_artist,
                'album': db_track.id3_album,
                'msec': db_track.msec,
                'composer': db_track.composer,
                'added': db_track.added,
            }
            track_dict = {
                'title': t['Name'],
                'artist': t['Artist'],
                'album': t['Album'],
                'msec': t['Total Time'],
                'composer': t.get('Composer', ''),
                'added': added,
            }

            if db_dict != track_dict:
                # we need to update an existing track
                changed = True
                field_alterations = [{
                    'field': k,
                    'from': db_dict[k],
                    'to': track_dict[k],
                } for k in db_dict.keys() if db_dict[k] != track_dict[k]]

        if new or changed:
            db_track.id = t['Persistent ID']
            db_track.id3_title = t['Name']
            db_track.id3_artist = t['Artist']
            db_track.id3_album = t['Album']
            db_track.msec = t['Total Time']
            db_track.composer = t.get('Composer', '')
            db_track.added = added
            db_track.inudesu = inudesu

        if new:
            if not inudesu:
                db_track.hidden = True
            else:
                db_track.hidden = False

            changes.append({
                'type': 'new',
                'item': unicode(db_track),
            })

        if changed:
            changes.append({
                'type': 'change',
                'item': unicode(db_track),
                'changes': field_alterations,
            })

        if (new or changed) and (not dry_run):
            db_track.save()

        tracks_kept.append(db_track)

    for track in [tr for tr in alltracks
                  if tr not in tracks_kept and not tr.hidden]:
        changes.append({
            'type': 'hide',
            'item': unicode(track),
        })
        if not dry_run:
            track.hidden = True
            track.save()

    return changes
