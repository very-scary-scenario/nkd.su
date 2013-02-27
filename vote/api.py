# Create your views here.
# -*- coding: utf-8 -*-

from vote.models import Week, Track
from vote.views import split_query_into_keywords, search_for_tracks

from django.http import HttpResponse, Http404
from django.shortcuts import redirect
from django.utils import timezone
from datetime import datetime
from django.utils import simplejson
from django.core.serializers.json import DjangoJSONEncoder
from django.core.paginator import Paginator, EmptyPage


def last_week(request):
    """ Redirect to last week """
    week = Week().prev()
    return redirect('/api/week/%s' % week.showtime.strftime('%d-%m-%Y'))


def week(request, date=None):
    """ Playlist archive """
    if date:
        day, month, year = (int(d) for d in date.split('-'))
        week = Week(timezone.make_aware(datetime(year, month, day),
                                        timezone.utc), correct=False)
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


def track(request, track_id):
    try:
        the_track = Track.objects.get(id=track_id)
    except Track.DoesNotExist:
        raise Http404

    json = jsonify(the_track.api_dict(verbose=True))
    return HttpResponse(json, mimetype='application/json')


def search(request):
    query = request.GET['q']
    if not 'page' in request.GET:
        pageno = 1
    else:
        try:
            pageno = int(request.GET['page'])
        except ValueError:
            raise Http404

    keyword_list = split_query_into_keywords(query)
    trackset = search_for_tracks(keyword_list,
                                 show_hidden=request.user.is_authenticated())

    paginator = Paginator(trackset, 100)
    try:
        page = paginator.page(pageno)
    except EmptyPage:
        raise Http404

    struc = {
        'results': [t.api_dict() for t in page.object_list],
        'page_count': paginator.num_pages,
        'results_count': paginator.count,
    }

    json = jsonify(struc)
    return HttpResponse(json, mimetype='application/json')


def jsonify(tree):
    return simplejson.dumps(tree, cls=DjangoJSONEncoder, indent=2)
