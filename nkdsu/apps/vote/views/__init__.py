from __future__ import annotations

import datetime
from random import sample
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple, Union, cast

from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.core.paginator import InvalidPage, Paginator
from django.db.models import Count, DurationField, F, QuerySet
from django.db.models.functions import Cast, Now
from django.forms import BaseForm
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.dateparse import parse_duration
from django.views.generic import DetailView, FormView, ListView, TemplateView
import tweepy

from ..forms import BadMetadataForm, DarkModeForm, RequestForm
from ..models import Show, Track, TwitterUser
from ..utils import BrowsableItem, BrowsableYear, reify
from ...vote import mixins


post_tw_auth = tweepy.OAuthHandler(settings.CONSUMER_KEY,
                                   settings.CONSUMER_SECRET)
post_tw_auth.set_access_token(settings.POSTING_ACCESS_TOKEN,
                              settings.POSTING_ACCESS_TOKEN_SECRET)
tw_api = tweepy.API(post_tw_auth)

PRO_ROULETTE = 'pro-roulette-{}'


class IndexView(mixins.CurrentShowMixin, TemplateView):
    section = 'home'
    template_name = 'index.html'

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        show = context['show']

        def track_should_be_in_main_list(track: Track) -> bool:
            if (
                self.request.user.is_authenticated and
                self.request.user.is_staff
            ):
                if track in show.shortlisted() or track in show.discarded():
                    return False

            if track in show.playlist():
                return False

            return True

        context['tracks'] = filter(track_should_be_in_main_list,
                                   show.tracks_sorted_by_votes())

        return context


class Browse(TemplateView):
    section = 'browse'
    template_name = 'browse.html'


class BrowseAnime(mixins.BrowseCategory):
    section = 'browse'
    category_name = 'anime'

    def get_categories(self) -> Iterable[BrowsableItem]:
        for title in Track.all_anime_titles():
            yield BrowsableItem(url=reverse("vote:anime", kwargs={"anime": title}), name=title)


class BrowseArtists(mixins.BrowseCategory):
    section = 'browse'
    category_name = 'artists'

    def get_categories(self) -> Iterable[BrowsableItem]:
        for artist in Track.all_artists():
            yield BrowsableItem(url=reverse("vote:artist", kwargs={"artist": artist}), name=artist)


class BrowseComposers(mixins.BrowseCategory):
    section = 'browse'
    category_name = 'composers'

    def get_categories(self) -> Iterable[BrowsableItem]:
        for composer in Track.all_composers():
            yield BrowsableItem(url=reverse("vote:composer", kwargs={"composer": composer}), name=composer)


class BrowseYears(mixins.BrowseCategory):
    section = 'browse'
    category_name = 'years'
    contents_required = False

    def get_categories(self) -> Iterable[BrowsableItem]:
        for year, has_tracks in Track.complete_decade_range():
            yield BrowsableYear(
                name=str(year),
                url=reverse("vote:year", kwargs={"year": year}) if has_tracks else None,
            )


class BrowseRoles(mixins.BrowseCategory):
    section = 'browse'
    template_name = 'browse_roles.html'
    category_name = 'roles'

    def get_categories(self) -> Iterable[BrowsableItem]:
        for role in Track.all_non_inudesu_roles():
            yield BrowsableItem(url=None, name=role)


class Archive(mixins.BreadcrumbMixin, mixins.ArchiveList):
    section = 'browse'
    template_name = 'archive.html'
    breadcrumbs = mixins.BrowseCategory.breadcrumbs

    def get_queryset(self) -> QuerySet[Show]:
        return super().get_queryset().filter(end__lt=timezone.now()).prefetch_related('play_set', 'vote_set')


class ShowDetail(mixins.ShowDetail):
    section = 'browse'
    template_name = 'show_detail.html'


class ListenRedirect(mixins.ShowDetail):
    section = 'browse'
    template_name = 'show_detail.html'

    def get(self, *a, **k) -> HttpResponse:
        super().get(*a, **k)
        cloudcasts = cast(Show, self.object).cloudcasts()
        if len(cloudcasts) == 1:
            return redirect(cloudcasts[0]['url'])
        elif len(cloudcasts) > 1:
            messages.warning(
                self.request,
                "There's more than one Mixcloud upload for this show. "
                "Please pick one of the {} listed below."
                .format(len(cloudcasts)),
            )
        else:
            messages.error(
                self.request,
                "Sorry, we couldn't find an appropriate Mixcloud upload to "
                "take you to.",
            )
        return redirect(cast(Show, self.object).get_absolute_url())


class Roulette(ListView):
    section = 'roulette'
    model = Track
    template_name = 'roulette.html'
    context_object_name = 'tracks'
    default_minutes_count = 1
    default_decade = 1980
    modes = [
        ('hipster', 'hipster'),
        ('indiscriminate', 'indiscriminate'),
        ('almost-100', 'almost 100'),
        ('decade', 'decade'),
        ('short', 'short'),
        ('staple', 'staple'),
        ('pro', 'pro (only for pros)'),
    ]

    def get(self, request, *args, **kwargs) -> HttpResponse:
        if (
            kwargs.get('mode') != 'pro' and
            self.request.session.get(self.pro_roulette_session_key())
        ):
            return redirect(reverse('vote:roulette',
                                    kwargs={'mode': 'pro'}))

        elif kwargs.get('mode') is None:
            if request.user.is_staff:
                mode = 'short'
            else:
                mode = 'hipster'
            return redirect(reverse('vote:roulette',
                                    kwargs={'mode': mode}))

        else:
            return super().get(request, *args, **kwargs)

    def pro_roulette_session_key(self) -> str:
        return PRO_ROULETTE.format(Show.current().pk)

    def pro_pk(self) -> int:
        sk = self.pro_roulette_session_key()
        pk = self.request.session.get(self.pro_roulette_session_key())

        if pk is None:
            for i in range(100):
                track = self.get_base_queryset().order_by('?')[0]
                if track.eligible():
                    break
            else:
                raise RuntimeError('are you sure anything is eligible')

            pk = track.pk
            session = self.request.session
            session[sk] = pk
            session.save()

        return pk

    def pro_queryset(self, qs):
        return qs.filter(pk=self.pro_pk())

    def get_base_queryset(self):
        return self.model.objects.public()

    def get_tracks(self) -> Tuple[Iterable[Track], int]:
        qs = self.get_base_queryset()

        if self.kwargs.get('mode') == 'pro':
            qs = self.pro_queryset(qs)
        elif self.kwargs.get('mode') == 'hipster':
            qs = qs.filter(play=None)
        elif self.kwargs.get('mode') == 'almost-100':
            qs = qs.exclude(
                play__date__gt=Show.current().end -
                datetime.timedelta(days=(7 * 80)),
            ).exclude(play=None)
        elif self.kwargs.get('mode') == 'decade':
            qs = qs.for_decade(int(self.kwargs.get('decade', self.default_decade)))
        elif self.kwargs.get('mode') == 'staple':
            # Staple track: having been played more than once per year(ish)
            # since the track was made available. Exclude tracks that don't
            # yet have enough plays to be reasonably called a "staple".
            qs = (
                qs.annotate(plays=Count('play'))
                .filter(plays__gt=2)
                .annotate(
                    time_per_play=Cast(
                        ((Now() - F('revealed')) / F('plays')),
                        output_field=DurationField()
                    )
                ).filter(time_per_play__lt=parse_duration('365 days'))
            )
            # order_by('?') fails when annotate() has been used
            return (sample(list(qs), 5), qs.count())
        elif self.kwargs.get('mode') == 'short':
            length_msec = int(
                self.kwargs.get('minutes', self.default_minutes_count)
            ) * 60 * 1000
            qs = qs.filter(msec__gt=length_msec - 60_000,
                           msec__lte=length_msec)

        return (qs.order_by('?')[:5], qs.count())

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        mode = self.kwargs['mode']
        decade_str = self.kwargs.get('decade', str(self.default_decade))
        minutes_str = self.kwargs.get('minutes', str(self.default_minutes_count))
        tracks, option_count = self.get_tracks()

        context.update({
            'decades': Track.all_decades(),
            'decade': int(decade_str) if decade_str else None,
            'minutes': int(minutes_str) if minutes_str else None,
            'allowed_minutes': (1, 2, 3),
            'mode': mode,
            'mode_name': dict(self.modes)[mode],
            'modes': self.modes,
            'tracks': tracks,
            'option_count': option_count,
        })

        return context


class Search(ListView):
    template_name = 'search.html'
    model = Track
    context_object_name = 'tracks'
    paginate_by = 20

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        resp = super().get(request, *args, **kwargs)
        qs = self.get_queryset()
        animes = set((
            role_detail.anime for t in qs for role_detail in t.role_details
        ))

        # if our search results are identical to an anime detail page, take us
        # there instead
        if len(animes) == 1:
            anime, = animes
            anime_qs = self.model.objects.by_anime(anime)

            if anime is not None and (
                sorted((t.pk for t in anime_qs)) == sorted((t.pk for t in qs))
            ):
                return redirect(reverse('vote:anime', kwargs={'anime': anime}))

        return resp

    @reify
    def _queryset(self) -> QuerySet[Track]:
        return self.model.objects.search(
            self.request.GET.get('q', ''),
            show_secret_tracks=(
                self.request.user.is_authenticated and
                self.request.user.is_staff
            ),
        )

    def get_queryset(self) -> QuerySet[Track]:
        return self._queryset

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        return context


class TrackDetail(DetailView):
    model = Track
    template_name = 'track_detail.html'
    context_object_name = 'track'

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        self.object = cast(Track, self.get_object())
        if kwargs.get('slug', None) != self.object.slug():
            return redirect(self.object.get_absolute_url())
        else:
            return super().get(request, *args, **kwargs)


class TwitterUserDetail(mixins.TwitterUserDetailMixin, DetailView):
    template_name = 'twitter_user_detail.html'
    context_object_name = 'voter'
    paginate_by = 100
    model = TwitterUser

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)

        votes = cast(TwitterUser, self.get_object()).votes_with_liberal_preselection()
        paginator = Paginator(votes, self.paginate_by)

        try:
            vote_page = paginator.page(self.request.GET.get('page', 1))
        except InvalidPage:
            raise Http404('Not a page')

        context.update({
            'votes': vote_page,
            'page_obj': vote_page,
        })

        return context


class TwitterAvatarView(mixins.TwitterUserDetailMixin, DetailView):
    model = TwitterUser

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        image: Union[bytes, str]
        content_type, image = cast(TwitterUser, self.get_object()).get_avatar(
            size='original' if request.GET.get('size') == 'original' else None)
        return HttpResponse(image, content_type=content_type)


class Year(mixins.BreadcrumbMixin, mixins.TrackListWithAnimeGrouping, ListView):
    section = 'browse'
    breadcrumbs = mixins.BrowseCategory.breadcrumbs + [(reverse_lazy('vote:browse_years'), 'years')]
    template_name = 'year.html'

    def get_track_queryset(self) -> QuerySet[Track]:
        return Track.objects.filter(year=int(self.kwargs['year']))

    def get_context_data(self):
        return {
            **super().get_context_data(),
            'year': self.kwargs['year'],
        }


class Artist(mixins.BreadcrumbMixin, mixins.TrackListWithAnimeGrouping, ListView):
    template_name = 'artist_detail.html'
    section = 'browse'
    breadcrumbs = mixins.BrowseCategory.breadcrumbs + [(reverse_lazy('vote:browse_artists'), 'artists')]

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        response = super().get(request, *args, **kwargs)

        if len(self.tracks) == 0:
            response.status_code = 404

        return response

    def get_track_queryset(self) -> QuerySet[Track]:
        return Track.objects.by_artist(
            self.kwargs['artist'], show_secret_tracks=(
                self.request.user.is_authenticated and
                self.request.user.is_staff
            )
        )

    def artist_suggestions(self) -> Set[str]:
        return Track.suggest_artists(self.kwargs['artist'])

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        self.tracks = context['tracks']
        context.update({
            'artist': self.kwargs['artist'],
            'played': [t for t in context['tracks'] if t.last_play()],
            'artist_suggestions': self.artist_suggestions,
            'tracks_as_composer': len(Track.objects.by_composer(self.kwargs['artist'])),
        })
        return context


class Anime(mixins.BreadcrumbMixin, ListView):
    section = 'browse'
    breadcrumbs = mixins.BrowseCategory.breadcrumbs + [(reverse_lazy('vote:browse_anime'), 'anime')]
    model = Track
    template_name = 'anime_detail.html'
    context_object_name = 'tracks'

    def get_queryset(self) -> List[Track]:  # type: ignore
        tracks = self.model.objects.by_anime(
            self.kwargs['anime'], show_secret_tracks=(
                self.request.user.is_authenticated and
                self.request.user.is_staff
            )
        )

        if len(tracks) == 0:
            raise Http404('No tracks for this anime')
        else:
            return sorted(
                tracks,
                key=lambda t: t.role_detail_for_anime(self.kwargs['anime'])
            )

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update({
            'anime': self.kwargs['anime'],
            'related_anime': (
                context['tracks'][0]
                .role_detail_for_anime(self.kwargs['anime']).related_anime
            )
        })
        return context


class Composer(mixins.BreadcrumbMixin, mixins.TrackListWithAnimeGrouping, ListView):
    section = 'browse'
    template_name = 'composer_detail.html'
    breadcrumbs = mixins.BrowseCategory.breadcrumbs + [(reverse_lazy('vote:browse_composers'), 'composers')]

    def get_track_queryset(self) -> QuerySet[Track]:
        if self.request.user.is_authenticated and self.request.user.is_staff:
            qs = Track.objects.all()
        else:
            qs = Track.objects.public()

        return qs.by_composer(self.kwargs['composer'])

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update({
            'composer': self.kwargs['composer'],
            'tracks_as_artist': len(Track.objects.by_artist(self.kwargs['composer'])),
        })
        return context


class Added(mixins.TrackListWithAnimeGrouping, mixins.ShowDetail):
    default_to_current = True
    section = 'new tracks'
    template_name = 'added.html'
    paginate_by = 50
    model = Show

    def get_track_queryset(self) -> QuerySet[Track]:
        return cast(Show, self.get_object()).revealed()


class Stats(TemplateView):
    section = 'stats'
    template_name = 'stats.html'
    cache_key = 'stats:context'

    def streaks(self) -> List[TwitterUser]:
        last_votable_show = Show.current().prev()
        while (
            last_votable_show is not None and
            not last_votable_show.voting_allowed
        ):
            last_votable_show = last_votable_show.prev()

        return sorted(
            TwitterUser.objects.filter(
                vote__show=last_votable_show,
            ).distinct(),
            key=lambda u: u.streak(),
            reverse=True
        )

    def batting_averages(self) -> List[TwitterUser]:
        users = []
        minimum_weight = 4

        cutoff = Show.at(timezone.now() -
                         datetime.timedelta(days=7*5)).end

        for user in set(TwitterUser.objects.filter(vote__date__gt=cutoff)):
            if user.batting_average(minimum_weight=minimum_weight):
                users.append(user)

        return sorted(users, key=lambda u: u.batting_average(
            minimum_weight=minimum_weight
        ) or 0, reverse=True)

    def popular_tracks(self) -> List[Tuple[Track, int]]:
        cutoff = Show.at(timezone.now() - datetime.timedelta(days=31*6)).end
        tracks = []

        for track in Track.objects.public():
            tracks.append((track, track.vote_set.filter(date__gt=cutoff).count()))

        return sorted(tracks, key=lambda t: t[1], reverse=True)

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
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


class ReportBadMetadata(mixins.BreadcrumbMixin, FormView):
    form_class = BadMetadataForm
    template_name = 'report.html'

    def get_track(self) -> Track:
        return get_object_or_404(Track, pk=self.kwargs['pk'])

    def get_context_data(self, *args, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(*args, **kwargs)
        context['track'] = self.get_track()
        return context

    def get_form_kwargs(self) -> Dict[str, Any]:
        kwargs = super().get_form_kwargs()
        kwargs['track'] = self.get_track()
        return kwargs

    def get_success_url(self) -> str:
        return self.get_track().get_absolute_url()

    def form_valid(self, form: BaseForm) -> HttpResponse:
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

        messages.success(
            self.request,
            'Your disclosure is appreciated. '
            'The metadata youkai has been dispatched to address your concerns.'
            ' None will know of its passing.'
        )

        return super().form_valid(form)

    def get_breadcrumbs(self) -> List[Tuple[Optional[str], str]]:
        track = self.get_track()

        return [
            (track.get_absolute_url(), track.title),
        ]


class RequestAddition(FormView):
    form_class = RequestForm
    template_name = 'request.html'
    success_url = reverse_lazy('vote:index')

    def get_initial(self) -> Dict[str, Any]:
        return {
            **super().get_initial(),
            **{k: v for (k, v) in self.request.GET.items()},
        }

    def form_valid(self, form: BaseForm) -> HttpResponse:
        f = form.cleaned_data

        fields = ['%s:\n%s' % (r, f[r]) for r in f if f[r]]

        send_mail(
            '[nkd.su] %s' % f['title'],
            '\n\n'.join(fields),
            '"nkd.su" <nkdsu@bldm.us>',
            [settings.REQUEST_CURATOR],
        )

        messages.success(
            self.request,
            'Your request has been dispatched. '
            'May it glide strong and true through spam filters and '
            'indifference.'
        )

        return super().form_valid(form)


class SetDarkModeView(FormView):
    http_method_names = ['post']
    form_class = DarkModeForm
    success_url = reverse_lazy('vote:index')

    def get_success_url(self) -> str:
        return self.request.META.get('HTTP_REFERER', self.success_url)

    def form_valid(self, form: BaseForm) -> HttpResponse:
        session = self.request.session
        session['dark_mode'] = {
            'light': False,
            'dark': True,
            'system': None,
        }[form.cleaned_data['mode']]
        session.save()
        return super().form_valid(form)

    def form_invalid(self, form: BaseForm) -> HttpResponse:
        return redirect(self.get_success_url())
