from django.http import HttpResponse
from django.views.generic import View

from ..models import Track
from ..utils import vote_tweet, tweet_url, length_str


class JSApiView(View):
    def post(self, request):
        result = self.do_thing(request.POST)
        return HttpResponse(result)


# javascript nonsense
def do_selection(request, select=True):
    """
    Returns the current selection, optionally selects or deselects a track.
    """

    return HttpResponse()  # XXX

    tracks = []

    if 'track_id[]' in request.POST:
        track_ids = dict(request.POST)[u'track_id[]']
        tracks = Track.objects.filter(id__in=track_ids)

    elif 'track_id' in request.POST:
        track_id = request.POST['track_id']
        tracks = (Track.objects.get(id=track_id),)

    # take our current selection list and turn it into a set
    if 'selection' in request.session:
        selection = set(request.session['selection'])
    else:
        selection = set()

    altered = False
    for track in tracks:
        # add or remove, as necessary
        altered = True
        if select:
            selection.add(track.id)
        else:
            try:
                selection.remove(track.id)
            except KeyError:
                # already not selected
                pass

    selection_queryset = Track.objects.filter(id__in=selection)

    # if our person is not authenticated, we have to be deselect things for
    # them when they stop being eligible or they might get pissed that their
    # vote didn't work
    redacted = False
    if not request.user.is_authenticated():
        for track in selection_queryset:
            if track.ineligible():
                selection.remove(track.id)
                redacted = True

    # only write if necessary
    if redacted:
        selection_queryset = Track.objects.filter(id__in=selection)
    if redacted or altered:
        request.session['selection'] = list(selection)

    tweet = vote_tweet(selection_queryset)
    vote_url = tweet_url(tweet)
    selection_len = length_str(total_length(selection_queryset))

    context = {
        'selection': selection_queryset,
        'vote_url': vote_url,
        'selection_len': selection_len,
        'tweet_is_too_long': tweet_len(tweet) > 140,
    }

    if request.method == 'GET':
        return redirect_nicely(request)
    elif request.method == 'POST':
        return render_to_response('minitracklist.html',
                                  RequestContext(request, context))


def do_select(request):
    return do_selection(request, True)


def do_deselect(request):
    return do_selection(request, False)


def do_clear_selection(request):
    request.session['selection'] = []
    return do_selection(request)
