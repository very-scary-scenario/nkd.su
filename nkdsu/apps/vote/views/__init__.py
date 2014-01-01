# -*- coding: utf-8 -*-

import datetime
from random import choice

from cache_utils.decorators import cached
import tweepy

from django.core.urlresolvers import reverse
from django.template import RequestContext
from django.http import Http404
from django.shortcuts import render_to_response, redirect
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from django.views.generic import TemplateView, ListView, DetailView

from .forms import RequestForm, BadMetadataForm
from ..vote import trivia, mixins
from ..vote.models import Show, Track, TwitterUser


post_tw_auth = tweepy.OAuthHandler(settings.CONSUMER_KEY,
                                   settings.CONSUMER_SECRET)
post_tw_auth.set_access_token(settings.POSTING_ACCESS_TOKEN,
                              settings.POSTING_ACCESS_TOKEN_SECRET)
tw_api = tweepy.API(post_tw_auth)


class IndexView(mixins.CurrentShowMixin, TemplateView):
    template_name = 'index.html'


class Archive(ListView):
    template_name = 'archive.html'
    paginate_by = 50

    def get_queryset(self):
        qs = Show.objects.filter(end__lt=timezone.now())
        return qs.order_by('-showtime')


class ShowDetail(mixins.ShowDetail):
    template_name = 'show_detail.html'


class Added(mixins.ShowDetail):
    template_name = 'added.html'


class Roulette(ListView):
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
        return self.model.objects.search(self.request.GET.get('q', ''))

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


class TwitterUserDetail(DetailView):
    model = TwitterUser
    template_name = 'twitter_user_detail.html'
    context_object_name = 'voter'

    def get_object(self):
        users = self.model.objects.filter(
            screen_name__iexact=self.kwargs['screen_name'])

        if not users.exists():
            raise Http404
        elif users.count() == 1:
            return users[0]
        else:
            return users.order_by('-updated')[0]


class Artist(ListView):
    model = Track
    template_name = 'artist_detail.html'
    context_object_name = 'tracks'

    def get_queryset(self):
        qs = self.model.objects.filter(
            id3_artist=self.kwargs['artist']).order_by('id3_title')

        if not qs.exists():
            raise Http404
        else:
            return qs

    def get_context_data(self):
        context = super(Artist, self).get_context_data()
        context['artist'] = self.kwargs['artist']
        return context


class Stats(TemplateView):
    template_name = 'stats.html'

    def batting_averages(self):
        users = []
        minimum_weight = 4

        for user in TwitterUser.objects.all():
            cutoff = Show.at(timezone.now() -
                             datetime.timedelta(days=7*5)).end
            if (
                user.vote_set.filter(date__gt=cutoff).exists() and
                user.batting_average(minimum_weight=minimum_weight)
            ):
                users.append(user)

        return sorted(users, key=lambda u: u.batting_average(
            minimum_weight=minimum_weight
        ), reverse=True)

    @cached(60*5)
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
            'batting_averages': self.batting_averages(),
            'popular_tracks': self.popular_tracks(),
        })
        return context


class Info(mixins.MarkdownView):
    title = 'what?'
    filename = 'README.md'


class APIDocs(mixins.MarkdownView):
    title = 'api'
    filename = 'API.md'


def report_bad_metadata(request, track_id):
    track = Track.objects.get(id=track_id)

    question = choice(trivia.questions.keys())
    d = {'trivia_question': question, 'track_id': track_id}

    if request.method == 'POST':
        form = BadMetadataForm(request.POST)
    else:
        form = BadMetadataForm(initial=d)

    if request.method == 'POST':
        if form.is_valid():
            f = form.cleaned_data

            fields = ['%s:\n%s' % (r, f[r]) for r in f if f[r]]
            fields.append(track.url())

            send_mail(
                '[nkd.su report] %s' % track.canonical_string(),
                '\n\n'.join(fields),
                '"nkd.su" <nkdsu@bldm.us>',
                [settings.REQUEST_CURATOR],
            )

            context = {'message': 'thanks for letting us know'}

            return render_to_response('message.html',
                                      RequestContext(request, context))

    form.fields['trivia'].label = 'Captcha: %s' % question
    form.data['trivia'] = ''
    form.data['trivia_question'] = question

    context = {
        'title': 'report bad metadata',
        'track': track,
        'form': form,
        'no_select': True,
    }

    return render_to_response('report.html', RequestContext(request, context))


def request_addition(request):
    question = choice(trivia.questions.keys())
    d = {'trivia_question': question}

    if 'q' in request.GET:
        d['title'] = request.GET['q']

    if request.method == 'POST':
        form = RequestForm(request.POST)
    else:
        form = RequestForm(initial=d)

    if request.method == 'POST':
        if form.is_valid():
            f = form.cleaned_data

            fields = ['%s:\n%s' % (r, f[r]) for r in f if f[r]]

            send_mail(
                '[nkd.su] %s' % f['title'],
                '\n\n'.join(fields),
                '"nkd.su" <nkdsu@bldm.us>',
                [settings.REQUEST_CURATOR],
            )

            context = {'message': 'thank you for your request'}

            return render_to_response('message.html',
                                      RequestContext(request, context))

    form.fields['trivia'].label = 'Captcha: %s' % question
    form.data['trivia'] = ''
    form.data['trivia_question'] = question

    context = {
        'title': 'request an addition',
        'form': form,
        'no_select': True,
    }

    return render_to_response('request.html', RequestContext(request, context))
