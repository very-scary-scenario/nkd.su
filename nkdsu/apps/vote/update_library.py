#!/usr/bin/env python

from models import Track
from Levenshtein import ratio
from django.utils.timezone import get_default_timezone, make_aware


def check_closeness_against_list(name, canonical_names, reverse=False):
    best_closeness, best_match = 0.7, None

    if name:
        if name in canonical_names:
            return None

        reversed_name = ' '.join(reversed(name.split()))
        if reverse:
            if reversed_name in canonical_names:
                return reversed_name
            else:
                names_to_check = (name, reversed_name)
        else:
            names_to_check = (name,)

        for canonical_name in canonical_names:
            for check_name in names_to_check:
                closeness = ratio(unicode(check_name.lower()),
                                  unicode(canonical_name.lower()))
                if closeness > best_closeness:
                    best_closeness = closeness
                    best_match = canonical_name

    return best_match


def metadata_consistency_checks(db_track, all_anime_titles, all_artists):
    warnings = []
    track_anime = db_track.role_detail.get('anime', '')
    track_role = db_track.role_detail.get('role', '')

    if not track_anime and not db_track.inudesu:
        warnings.append({
            'field': 'anime',
            'message': 'field is missing'
        })

    if not track_role and not db_track.inudesu:
        warnings.append({
            'field': 'role',
            'message': 'field is missing'
        })

    if track_anime:
        match = check_closeness_against_list(track_anime, all_anime_titles)
        if match:
            warnings.append({
                'field': 'anime',
                'message': (
                    u'"{track_anime}" was not found in the database, but it '
                    u'looks similar to "{canonical_anime}", which is'
                ).format(track_anime=track_anime, canonical_anime=match)
            })

    for artist in db_track.artists():
        artist_name = artist.get('name', '')
        match = check_closeness_against_list(artist_name, all_artists,
                                             reverse=True)
        if match:
            warnings.append({
                'field': 'artist',
                'message': (
                    u'"{track_artist}" was not found in the database, but it '
                    u'looks similar to "{canonical_artist}", which is'
                ).format(track_artist=artist, canonical_artist=match)
            })

    return warnings


def update_library(tree, dry_run=False, inudesu=False):
    changes = []
    alltracks = Track.objects.filter(inudesu=inudesu)
    all_anime_titles = Track.all_anime_titles()
    all_artists = Track.all_artists()
    tracks_kept = []
    for tid in tree['Tracks']:
        changed = False
        new = False
        warnings = []
        field_alterations = []

        t = tree['Tracks'][tid]
        added = make_aware(t['Date Added'], get_default_timezone())

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

            for field, value in track_dict.iteritems():
                if (
                    isinstance(value, (str, unicode)) and
                    (value.strip() != value)
                ):
                    warnings.append({
                        'field': field,
                        'message': 'leading or trailing whitespace',
                    })

        if new or changed:
            db_track.id = t['Persistent ID']
            db_track.id3_title = t['Name']
            db_track.id3_artist = t['Artist']
            db_track.id3_album = t['Album']
            db_track.msec = t['Total Time']
            db_track.composer = t.get('Composer', '')
            db_track.added = added
            db_track.inudesu = inudesu
            warnings.extend(
                metadata_consistency_checks(
                    db_track, all_anime_titles, all_artists
                )
            )

        if new:
            if not inudesu:
                db_track.hidden = True
            else:
                db_track.hidden = False

            changes.append({
                'type': 'new',
                'item': unicode(db_track),
            })

        if changed or warnings:
            changes.append({
                'type': 'change',
                'item': unicode(db_track),
                'changes': field_alterations,
                'warnings': warnings
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
