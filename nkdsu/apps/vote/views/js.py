from typing import Optional

from django.conf import settings
from django.http import HttpResponse
from django.views.generic import TemplateView

from ..models import Track
from ..utils import tweet_len, tweet_url, vote_tweet


class JSApiMixin(object):
    # Yes, it's traversed like HTML, but it's *not* HTML. None of these even
    # have <html> elements.
    content_type: Optional[str] = 'text/plain'

    def post(self, request):
        result = self.do_thing(request.POST)
        return HttpResponse(result, content_type=self.content_type)


class SelectionView(JSApiMixin, TemplateView):
    template_name = 'minitracklist.html'
    model = Track

    def get_queryset(self):
        return self.model.objects.filter(
            pk__in=self.request.session.get('selection', set()))

    def post(self, request, *args, **kwargs):
        self.request = request
        self.do_thing()

        context = {}

        selection = self.get_queryset()
        context['selection'] = selection

        tweet = vote_tweet(selection)
        if tweet_len(tweet) <= settings.TWEET_LENGTH:
            context['vote_url'] = tweet_url(tweet)

        return self.render_to_response(context)


class GetSelection(SelectionView):
    def do_thing(self) -> None:
        pass


class Select(SelectionView):
    def do_thing(self) -> None:
        new_pks: list[str] = self.request.POST.getlist('track_pk[]', [])
        selection = set(self.request.session.get('selection', []))

        for new_pk in new_pks:
            if (
                self.request.user.is_authenticated
            ):
                base_qs = Track.objects.all()
            else:
                base_qs = Track.objects.public()

            qs = base_qs.filter(pk=new_pk)
            if qs.exists():
                track = qs[0]
                if (
                    self.request.user.is_authenticated and
                    self.request.user.is_staff
                ) or track.eligible():
                    selection.add(new_pk)

        self.request.session['selection'] = sorted(selection)


class Deselect(SelectionView):
    def do_thing(self) -> None:
        unwanted_pks: list[str] = self.request.POST.getlist('track_pk[]', [])
        selection = set(self.request.session.get('selection', []))

        for unwanted_pk in unwanted_pks:
            if unwanted_pk in selection:
                selection.remove(unwanted_pk)

        self.request.session['selection'] = sorted(selection)


class ClearSelection(SelectionView):
    def do_thing(self) -> None:
        self.request.session['selection'] = []
