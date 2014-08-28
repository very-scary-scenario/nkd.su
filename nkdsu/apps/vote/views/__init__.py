import datetime

import tweepy

from django.core.urlresolvers import reverse, reverse_lazy
from django.core.paginator import Paginator, InvalidPage
from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect, get_object_or_404
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from django.views.generic import TemplateView, ListView, DetailView, FormView

from ..forms import RequestForm, BadMetadataForm
from ...vote import mixins
from ...vote.models import Show, Track, TwitterUser


post_tw_auth = tweepy.OAuthHandler(settings.CONSUMER_KEY,
                                   settings.CONSUMER_SECRET)
post_tw_auth.set_access_token(settings.POSTING_ACCESS_TOKEN,
                              settings.POSTING_ACCESS_TOKEN_SECRET)
tw_api = tweepy.API(post_tw_auth)


class IndexView(mixins.CurrentShowMixin, TemplateView):
    section = 'home'
    template_name = 'index.html'

    def get_context_data(self):
        context = super(IndexView, self).get_context_data()
        show = context['show']

        def track_should_be_in_main_list(track):
            if self.request.user.is_authenticated():
                if track in show.shortlisted() or track in show.discarded():
                    return False

            if track in show.playlist():
                return False

            return True

        context['tracks'] = filter(track_should_be_in_main_list,
                                   show.tracks_sorted_by_votes())

        return context


class Archive(ListView):
    section = 'archive'
    template_name = 'archive.html'
    paginate_by = 50

    def get_queryset(self):
        qs = Show.objects.filter(end__lt=timezone.now())
        return qs.order_by('-showtime').prefetch_related(
            'play_set', 'vote_set')


class ShowDetail(mixins.ShowDetail):
    section = 'archive'
    template_name = 'show_detail.html'


class Added(mixins.ShowDetailMixin, ListView):
    section = 'new tracks'
    template_name = 'added.html'
    paginate_by = 50

    def get_queryset(self):
        return self.get_object().revealed()


class Roulette(ListView):
    section = 'roulette'
    model = Track
    template_name = 'roulette.html'
    context_object_name = 'tracks'

    def get(self, request, *args, **kwargs):
        if kwargs.get('mode') is None:
            return redirect(reverse('vote:roulette',
                                    kwargs={'mode': 'hipster'}))
        else:
            return super(Roulette, self).get(request, *args, **kwargs)

    def get_queryset(self):
        qs = self.model.objects.public()

        if self.kwargs.get('mode') != 'indiscriminate':
            qs = qs.filter(play=None)

        return qs.order_by('?')[:5]

    def get_context_data(self):
        context = super(Roulette, self).get_context_data()
        context['mode'] = self.kwargs.get('mode') or 'hipster'
        context['modes'] = ['hipster', 'indiscriminate']
        return context


class Search(ListView):
    template_name = 'search.html'
    model = Track
    context_object_name = 'tracks'
    paginate_by = 20

    def get_queryset(self):
        return self.model.objects.search(
            self.request.GET.get('q', ''),
            show_secret_tracks=self.request.user.is_authenticated(),
        )

    def get_context_data(self):
        context = super(Search, self).get_context_data()
        context['query'] = self.request.GET.get('q', '')
        return context


class TrackDetail(DetailView):
    model = Track
    template_name = 'track_detail.html'
    context_object_name = 'track'

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if kwargs.get('slug', None) != self.object.slug():
            return redirect(self.object.get_absolute_url())
        else:
            return super(TrackDetail, self).get(request, *args, **kwargs)


class TwitterUserDetail(mixins.TwitterUserDetailMixin, DetailView):
    template_name = 'twitter_user_detail.html'
    context_object_name = 'voter'
    paginate_by = 100

    def get_context_data(self, *args, **kwargs):
        context = super(TwitterUserDetail, self).get_context_data(*args,
                                                                  **kwargs)

        votes = self.get_object().votes_with_liberal_preselection()
        paginator = Paginator(votes, self.paginate_by)

        try:
            votes = paginator.page(self.request.GET.get('page', 1))
        except InvalidPage:
            raise Http404('Not a page')

        context.update({
            'votes': votes,
            'page_obj': votes,
        })

        return context


class Artist(ListView):
    model = Track
    template_name = 'artist_detail.html'
    context_object_name = 'tracks'

    def get_queryset(self):
        tracks = self.model.objects.by_artist(self.kwargs['artist'])

        if len(tracks) == 0:
            raise Http404('No tracks for this artist')
        else:
            return tracks

    def get_context_data(self):
        context = super(Artist, self).get_context_data()
        context['artist'] = self.kwargs['artist']
        return context


class Stats(TemplateView):
    section = 'stats'
    template_name = 'stats.html'
    cache_key = 'stats:context'

    def streaks(self):
        return sorted(
            TwitterUser.objects.filter(
                vote__show=Show.current().prev()
            ).distinct(),
            key=lambda u: u.streak(),
            reverse=True
        )

    def batting_averages(self):
        users = []
        minimum_weight = 4

        cutoff = Show.at(timezone.now() -
                         datetime.timedelta(days=7*5)).end

        for user in set(TwitterUser.objects.filter(vote__date__gt=cutoff)):
            if user.batting_average(minimum_weight=minimum_weight):
                users.append(user)

        return sorted(users, key=lambda u: u.batting_average(
            minimum_weight=minimum_weight
        ), reverse=True)

    def popular_tracks(self):
        cutoff = Show.at(timezone.now() - datetime.timedelta(days=31*6)).end
        tracks = []

        for track in Track.objects.public():
            tracks.append((track,
                           track.vote_set.filter(date__gt=cutoff).count()))

        return sorted(tracks, key=lambda t: t[1], reverse=True)

    def get_context_data(self):
        context = super(Stats, self).get_context_data()
        context.update({
            'streaks': self.streaks,
            'batting_averages': self.batting_averages,
            'popular_tracks': self.popular_tracks,
        })
        return context


class Info(mixins.MarkdownView):
    title = 'what?'
    filename = 'README.md'


class APIDocs(mixins.MarkdownView):
    title = 'api'
    filename = 'API.md'


class ReportBadMetadata(FormView):
    form_class = BadMetadataForm
    template_name = 'report.html'

    def get_track(self):
        return get_object_or_404(Track, pk=self.kwargs['pk'])

    def get_context_data(self, *args, **kwargs):
        context = super(ReportBadMetadata, self).get_context_data(*args,
                                                                  **kwargs)
        context['track'] = self.get_track()
        return context

    def get_success_url(self):
        return self.get_track().get_absolute_url()

    def form_valid(self, form):
        f = form.cleaned_data

        track = Track.objects.get(pk=self.kwargs['pk'])

        fields = ['%s:\n%s' % (r, f[r]) for r in f if f[r]]
        fields.append(track.get_public_url())

        send_mail(
            '[nkd.su report] %s' % track.get_absolute_url(),
            '\n\n'.join(fields),
            '"nkd.su" <nkdsu@bldm.us>',
            [settings.REQUEST_CURATOR],
        )

        messages.add_message(
            self.request, messages.SUCCESS,
            'Your disclosure is appreciated. '
            'The metadata youkai has been dispatched to address your concerns.'
            ' None will know of its passing.'
        )

        return super(ReportBadMetadata, self).form_valid(form)


class RequestAddition(FormView):
    form_class = RequestForm
    template_name = 'request.html'
    success_url = reverse_lazy('vote:index')

    def form_valid(self, form):
        f = form.cleaned_data

        fields = ['%s:\n%s' % (r, f[r]) for r in f if f[r]]

        send_mail(
            '[nkd.su] %s' % f['title'],
            '\n\n'.join(fields),
            '"nkd.su" <nkdsu@bldm.us>',
            [settings.REQUEST_CURATOR],
        )

        messages.add_message(
            self.request, messages.SUCCESS,
            'Your request has been dispatched. '
            'May it glide strong and true through spam filters and '
            'indifference.'
        )

        return super(RequestAddition, self).form_valid(form)
