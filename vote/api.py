# Create your views here.
# -*- coding: utf-8 -*-

from vote.models import Week, Track

from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils import timezone
from datetime import datetime
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

    this_week = Week()

    tracks = [p.track for p in plays]
    [setattr(t, '_vote_week', week) for t in tracks]
    [setattr(t, '_current_week', this_week) for t in tracks]

    votes = week._votes()

    the_show = {
            'playlist': [{
                'time': p.datetime,
                'track': p.track.api_dict(),
                } for p in plays],
            'added': [t.api_dict() for t in week.added()],
            'votes': [v.api_dict() for v in votes],
            'start': week.start,
            'showtime': week.showtime,
            'finish': week.finish,
        }

    json = jsonify(the_show)

    return HttpResponse(json, mimetype='application/json')

def track(response, track_id):
    the_track = Track.objects.get(id=track_id)
    json = jsonify(the_track.api_dict(verbose=True))
    return HttpResponse(json, mimetype='application/json')

def jsonify(tree):
    return simplejson.dumps(tree, cls=DjangoJSONEncoder, indent=2)
