# Create your views here.
# -*- coding: utf-8 -*-

from vote.models import *

from django.template import RequestContext, loader
from django.http import HttpResponse, Http404
from django.shortcuts import render_to_response, redirect
from django.utils import timezone
from datetime import date, timedelta, datetime
from django.utils import simplejson
from django.core.serializers.json import DjangoJSONEncoder


def last_week(request):
    """ Redirect to the show containing the latest play """
    week = Week().prev()
    return redirect('/api/week/%s' % week.showtime.strftime('%d-%m-%Y'))

def week(request, date=None):
    """ Playlist archive """
    if date:
        day, month, year = (int(t) for t in date.split('-'))
        week = Week(timezone.make_aware(datetime(year, month, day), timezone.utc), correct=False)
    else:
        week = Week()

    plays = week.plays()

    next_week = week.next()
    if next_week.finish < timezone.now() and next_week.has_plays():
        next_show = next_week.showtime
    else: next_show = None

    prev_week = week.prev()
    if prev_week.has_plays(): prev_show = prev_week.showtime
    else: prev_show = None
    
    this_week = Week()

    tracks = [p.track for p in plays]
    [setattr(t, '_vote_week', week) for t in tracks]
    [setattr(t, '_current_week', this_week) for t in tracks]

    votes = week.votes()
    tracks_added_this_week = len(week.added())

    the_show = {
            'playlist': [{
                'time': p.datetime,
                'track': {
                    'id': p.track.id,
                    'title': p.track.derived_title(),
                    'role': p.track.derived_role(),
                    'artist': p.track.id3_artist,
                    },
                } for p in plays],

            'votes': [{
                'user_name': v.name,
                'user_screen_name': v.screen_name,
                'user_image': v.user_image,
                'user_id': v.user_id,
                'tweet_id': v.tweet_id,
                'comment': v.content() if v.content() != '' else None,
                'time': v.date,
                'track_ids': [t.id for t in v.get_tracks()],
                } for v in votes],

            'start': week.start,
            'showtime': week.showtime,
            'finish': week.finish,
        }

    json = simplejson.dumps(the_show, cls=DjangoJSONEncoder, indent=2)

    return HttpResponse(json, mimetype='application/json')
