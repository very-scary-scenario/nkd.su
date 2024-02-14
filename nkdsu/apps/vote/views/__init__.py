from __future__ import annotations

import datetime
from abc import abstractmethod
from functools import cached_property
from itertools import chain
from random import sample
from typing import Any, Iterable, Optional, Sequence, cast

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import AnonymousUser
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
from django.views.generic import (
    CreateView,
    DetailView,
    FormView,
    ListView,
    TemplateView,
    UpdateView,
)

from nkdsu.mixins import MarkdownView
from ..anime import suggest_anime
from ..forms import BadMetadataForm, DarkModeForm, RequestForm, VoteForm
from ..models import (
    Profile,
    Request,
    Role,
    Show,
    Track,
    TrackQuerySet,
    TwitterUser,
    Vote,
)
from ..templatetags.vote_tags import eligible_for
from ..utils import BrowsableItem, BrowsableYear, vote_edit_cutoff
from ..voter import Voter
from ...vote import mixins


PRO_ROULETTE = 'pro-roulette-{}'


class IndexView(mixins.CurrentShowMixin, TemplateView):
    section = 'home'
    template_name = 'index.html'

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        show = context['show']

        def track_should_be_in_main_list(track: Track) -> bool:
            if self.request.user.is_authenticated and self.request.user.is_staff:
                if track in show.shortlisted() or track in show.discarded():
                    return False

            if track in show.playlist():
                return False

            return True

        context['tracks'] = filter(
            track_should_be_in_main_list, show.tracks_sorted_by_votes()
        )

        return context


class Browse(TemplateView):
    section = 'browse'
    template_name = 'browse.html'


class BrowseAnime(mixins.BrowseCategory):
    section = 'browse'
    category_name = 'anime'

    def get_categories(self) -> Iterable[BrowsableItem]:
        for title in Track.all_anime_titles():
            yield BrowsableItem(
                url=reverse("vote:anime", kwargs={"anime": title}), name=title
            )


class BrowseArtists(mixins.BrowseCategory):
    section = 'browse'
    category_name = 'artists'

    def get_categories(self) -> Iterable[BrowsableItem]:
        for artist in Track.all_artists():
            yield BrowsableItem(
                url=reverse("vote:artist", kwargs={"artist": artist}), name=artist
            )


class BrowseComposers(mixins.BrowseCategory):
    section = 'browse'
    category_name = 'composers'

    def get_categories(self) -> Iterable[BrowsableItem]:
        for composer in Track.all_composers():
            yield BrowsableItem(
                url=reverse("vote:composer", kwargs={"composer": composer}),
                name=composer,
            )


class BrowseYears(mixins.BrowseCategory):
    section = 'browse'
    category_name = 'years'
    contents_required = False
    searchable = False

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
        return (
            super()
            .get_queryset()
            .filter(end__lt=timezone.now())
            .prefetch_related('play_set', 'vote_set')
        )


class ShowDetail(mixins.BreadcrumbMixin, mixins.ShowDetail):
    section = 'browse'
    template_name = 'show_detail.html'
    breadcrumbs = mixins.BrowseCategory.breadcrumbs + [
        (reverse_lazy('vote:archive'), 'past shows')
    ]
    model = Show
    object: Show


class ListenRedirect(mixins.ShowDetail):
    section = 'browse'
    template_name = 'show_detail.html'

    def get(self, *a, **k) -> HttpResponse:
        super().get(*a, **k)
        cloudcasts = self.object.cloudcasts()
        if len(cloudcasts) == 1:
            return redirect(cloudcasts[0]['url'])
        elif len(cloudcasts) > 1:
            messages.warning(
                self.request,
                "There's more than one Mixcloud upload for this show. "
                "Please pick one of the {} listed below.".format(len(cloudcasts)),
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
        if kwargs.get('mode') != 'pro' and self.request.session.get(
            self.pro_roulette_session_key()
        ):
            return redirect(reverse('vote:roulette', kwargs={'mode': 'pro'}))

        elif kwargs.get('mode') is None:
            if request.user.is_staff:
                mode = 'short'
            else:
                mode = 'hipster'
            return redirect(reverse('vote:roulette', kwargs={'mode': mode}))

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

    def get_tracks(self) -> tuple[Iterable[Track], int]:
        qs = self.get_base_queryset()

        if self.kwargs.get('mode') == 'pro':
            qs = self.pro_queryset(qs)
        elif self.kwargs.get('mode') == 'hipster':
            qs = qs.filter(play=None)
        elif self.kwargs.get('mode') == 'almost-100':
            qs = qs.exclude(
                play__date__gt=Show.current().end - datetime.timedelta(days=(7 * 80)),
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
                        output_field=DurationField(),
                    )
                )
                .filter(time_per_play__lt=parse_duration('365 days'))
            )
            # order_by('?') fails when annotate() has been used
            return (sample(list(qs), 5), qs.count())
        elif self.kwargs.get('mode') == 'short':
            length_msec = (
                int(self.kwargs.get('minutes', self.default_minutes_count)) * 60 * 1000
            )
            qs = qs.filter(msec__gt=length_msec - 60_000, msec__lte=length_msec)

        return (qs.order_by('?')[:5], qs.count())

    def get_context_data(self, **kwargs) -> dict[str, Any]:
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
        track_animes: set[str] = set((
            role_detail.anime
            for t in qs
            for role_detail in t.role_details
            if role_detail.anime is not None
        ))
        all_animes = track_animes | self.anime_suggestions

        # if our search results are identical to an anime detail page, or if
        # there's one suggestion and no results, take us there instead
        if len(all_animes) == 1:
            (anime,) = all_animes
            anime_qs = self.model.objects.by_anime(anime)

            if anime is not None and (
                (not qs)
                or sorted((t.pk for t in anime_qs)) == sorted((t.pk for t in qs))
            ):
                return redirect(reverse('vote:anime', kwargs={'anime': anime}))

        return resp

    @cached_property
    def _queryset(self) -> TrackQuerySet:
        return self.model.objects.search(
            self.request.GET.get('q', ''),
            show_secret_tracks=(
                self.request.user.is_authenticated and self.request.user.is_staff
            ),
        )

    def get_queryset(self) -> QuerySet[Track]:
        return self._queryset

    @cached_property
    def anime_suggestions(self) -> set[str]:
        query = self.request.GET.get('q')
        return set() if query is None else suggest_anime(query)

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get('q', '')
        context.update({
            'query': query,
            'anime_suggestions': self.anime_suggestions,
        })
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


class VoterDetail(DetailView):
    paginate_by = 100

    @abstractmethod
    def get_voter(self) -> Voter: ...

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)

        votes = cast(Voter, self.get_voter()).votes_with_liberal_preselection()
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


class TwitterUserDetail(mixins.TwitterUserDetailMixin, VoterDetail):
    template_name = 'twitter_user_detail.html'
    context_object_name = 'voter'
    model = TwitterUser

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        twu = self.get_object()
        if hasattr(twu, 'profile'):
            return redirect(twu.profile.get_absolute_url())
        else:
            return super().get(request, *args, **kwargs)

    def get_voter(self) -> TwitterUser:
        return self.get_object()


class UpdateVoteView(LoginRequiredMixin, UpdateView):
    template_name = 'vote_edit.html'
    fields = ['text']

    def get_queryset(self) -> QuerySet[Vote]:
        # enforced by LoginRequiredMixin:
        assert not isinstance(self.request.user, AnonymousUser)
        return Vote.objects.filter(
            user=self.request.user, show__showtime__gte=vote_edit_cutoff().showtime
        )

    def get_success_url(self) -> str:
        return reverse('vote:profiles:profile', kwargs={'username': self.object.user})


class Year(mixins.BreadcrumbMixin, mixins.TrackListWithAnimeGroupingListView):
    section = 'browse'
    breadcrumbs = mixins.BrowseCategory.breadcrumbs + [
        (reverse_lazy('vote:browse_years'), 'years')
    ]
    template_name = 'year.html'

    def get_track_queryset(self) -> TrackQuerySet:
        return Track.objects.public().filter(year=int(self.kwargs['year']))

    def get_context_data(self):
        year = int(self.kwargs['year'])

        def year_if_tracks_exist(year: int) -> Optional[int]:
            return year if Track.objects.public().filter(year=year) else None

        return {
            **super().get_context_data(),
            'year': year,
            'previous_year': year_if_tracks_exist(year - 1),
            'next_year': year_if_tracks_exist(year + 1),
        }


class Artist(mixins.BreadcrumbMixin, mixins.TrackListWithAnimeGroupingListView):
    template_name = 'artist_detail.html'
    section = 'browse'
    breadcrumbs = mixins.BrowseCategory.breadcrumbs + [
        (reverse_lazy('vote:browse_artists'), 'artists')
    ]

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        response = super().get(request, *args, **kwargs)

        if len(self.tracks) == 0:
            response.status_code = 404

        return response

    def get_track_queryset(self) -> Sequence[Track]:
        return Track.objects.by_artist(
            self.kwargs['artist'],
            show_secret_tracks=(
                self.request.user.is_authenticated and self.request.user.is_staff
            ),
        )

    def artist_suggestions(self) -> set[str]:
        return Track.suggest_artists(self.kwargs['artist'])

    def get_context_data(self, **kwargs) -> dict[str, Any]:
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
    breadcrumbs = mixins.BrowseCategory.breadcrumbs + [
        (reverse_lazy('vote:browse_anime'), 'anime')
    ]
    model = Track
    template_name = 'anime_detail.html'
    context_object_name = 'tracks'

    def get_queryset(self) -> list[Track]:
        tracks = self.model.objects.by_anime(
            self.kwargs['anime'],
            show_secret_tracks=(
                self.request.user.is_authenticated and self.request.user.is_staff
            ),
        )

        if len(tracks) == 0:
            raise Http404('No tracks for this anime')
        else:
            return tracks

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        role_tracks: list[tuple[Role, Track]] = sorted(
            (
                (role, track)
                for track in context[self.context_object_name]
                for role in track.role_details_for_anime(self.kwargs['anime'])
            ),
            key=lambda rt: rt[0],
        )
        context.update({
            'anime': self.kwargs['anime'],
            'role_tracks': role_tracks,
            'related_anime': (
                context['tracks'][0]
                .role_details_for_anime(self.kwargs['anime'])[0]
                .related_anime
            ),
        })
        return context


class AnimePicture(Anime):
    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        tracks = self.get_queryset()
        anime_data = tracks[0].role_details[0].anime_data()
        if anime_data is None:
            raise Http404()
        return redirect(anime_data.cached_picture_url())


class Composer(mixins.BreadcrumbMixin, mixins.TrackListWithAnimeGroupingListView):
    section = 'browse'
    template_name = 'composer_detail.html'
    breadcrumbs = mixins.BrowseCategory.breadcrumbs + [
        (reverse_lazy('vote:browse_composers'), 'composers')
    ]

    def get_track_queryset(self) -> Sequence[Track]:
        if self.request.user.is_authenticated and self.request.user.is_staff:
            qs = Track.objects.all()
        else:
            qs = Track.objects.public()

        return qs.by_composer(self.kwargs['composer'])

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update({
            'composer': self.kwargs['composer'],
            'tracks_as_artist': len(Track.objects.by_artist(self.kwargs['composer'])),
        })
        return context


class Added(
    mixins.BreadcrumbMixin, mixins.TrackListWithAnimeGrouping, mixins.ShowDetail
):
    default_to_current = True
    section = 'new tracks'
    template_name = 'added.html'
    paginate_by = 50
    breadcrumbs = mixins.BrowseCategory.breadcrumbs + [
        (reverse_lazy('vote:archive'), 'past shows')
    ]
    model = Show
    object: Show

    def get_track_queryset(self) -> TrackQuerySet:
        return self.get_object().revealed()


class Stats(TemplateView):
    section = 'stats'
    template_name = 'stats.html'
    cache_key = 'stats:context'

    def unique_voters(
        self, profiles: QuerySet[Profile], twitter_users: QuerySet[TwitterUser]
    ) -> list[Voter]:
        seen_ids: set[tuple[Optional[int], Optional[int]]] = set()
        voters: list[Voter] = []

        for voter in chain(profiles, twitter_users):
            vid = voter.voter_id
            if vid not in seen_ids:
                voters.append(voter)
                seen_ids.add(voter.voter_id)

        return voters

    def streaks(self) -> list[Voter]:
        last_votable_show = Show.current().prev()
        while last_votable_show is not None and not last_votable_show.voting_allowed:
            last_votable_show = last_votable_show.prev()

        return sorted(
            self.unique_voters(
                Profile.objects.filter(user__vote__show=last_votable_show),
                TwitterUser.objects.filter(vote__show=last_votable_show),
            ),
            key=lambda u: u.streak(),
            reverse=True,
        )

    def batting_averages(self) -> list[Voter]:
        users = []
        minimum_weight = 4

        cutoff = Show.at(timezone.now() - datetime.timedelta(days=7 * 5)).end

        for user in self.unique_voters(
            Profile.objects.filter(user__vote__date__gt=cutoff),
            TwitterUser.objects.filter(vote__date__gt=cutoff),
        ):
            if user.batting_average(minimum_weight=minimum_weight):
                users.append(user)

        return sorted(
            users,
            key=lambda u: u.batting_average(minimum_weight=minimum_weight) or 0,
            reverse=True,
        )

    def popular_tracks(self) -> list[tuple[Track, int]]:
        cutoff = Show.at(timezone.now() - datetime.timedelta(days=31 * 6)).end
        tracks = []

        for track in Track.objects.public():
            tracks.append((track, track.vote_set.filter(date__gt=cutoff).count()))

        return sorted(tracks, key=lambda t: t[1], reverse=True)

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update({
            'streaks': self.streaks,
            'batting_averages': self.batting_averages,
            'popular_tracks': self.popular_tracks,
        })
        return context


class Info(MarkdownView):
    title = 'what?'
    filename = 'README.md'


class APIDocs(MarkdownView):
    title = 'api'
    filename = 'API.md'


class Privacy(MarkdownView):
    title = 'privacy'
    filename = 'PRIVACY.md'


class TermsOfService(MarkdownView):
    title = 'tos'
    filename = 'TOS.md'


class ReportBadMetadata(LoginRequiredMixin, mixins.BreadcrumbMixin, FormView):
    form_class = BadMetadataForm
    template_name = 'report.html'

    def get_track(self) -> Track:
        return get_object_or_404(Track, pk=self.kwargs['pk'])

    def get_context_data(self, *args, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(*args, **kwargs)
        context['track'] = self.get_track()
        return context

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        kwargs['track'] = self.get_track()
        return kwargs

    def get_success_url(self) -> str:
        return self.get_track().get_absolute_url()

    def form_valid(self, form: BaseForm) -> HttpResponse:
        track = Track.objects.get(pk=self.kwargs['pk'])

        assert self.request.user.is_authenticated  # guaranteed by LoginRequiredMixin

        request = Request(submitted_by=self.request.user, track=track)
        request.serialise(form.cleaned_data)
        request.save()

        f = form.cleaned_data
        fields = ['%s:\n%s' % (r, f[r]) for r in f if f[r]]
        fields.append(track.get_public_url())
        send_mail(
            '[nkd.su report] %s' % track.get_absolute_url(),
            '\n\n'.join(fields),
            f'"nkd.su" <{settings.EMAIL_HOST_USER}>',
            [settings.REQUEST_CURATOR],
        )

        messages.success(
            self.request,
            'Your disclosure is appreciated. '
            'The metadata youkai has been dispatched to address your concerns.'
            ' None will know of its passing.',
        )

        return super().form_valid(form)

    def get_breadcrumbs(self) -> list[tuple[Optional[str], str]]:
        track = self.get_track()

        return [
            (track.get_absolute_url(), track.title),
        ]


class RequestAddition(LoginRequiredMixin, MarkdownView, FormView):
    form_class = RequestForm
    template_name = 'request.html'
    success_url = reverse_lazy('vote:index')
    filename = 'ELIGIBILITY.md'
    title = 'Request an addition to the library'

    def get_initial(self) -> dict[str, Any]:
        return {
            **super().get_initial(),
            **{k: v for (k, v) in self.request.GET.items()},
        }

    def form_valid(self, form: BaseForm) -> HttpResponse:
        assert self.request.user.is_authenticated  # guaranteed by LoginRequiredMixin
        request = Request(submitted_by=self.request.user)
        request.serialise(form.cleaned_data)
        request.save()

        f = form.cleaned_data
        fields = ['%s:\n%s' % (r, f[r]) for r in f if f[r]]
        send_mail(
            '[nkd.su] %s' % f['title'],
            '\n\n'.join(fields),
            '"nkd.su" <noreply@vscary.co>',
            [settings.REQUEST_CURATOR],
        )

        messages.success(
            self.request,
            'Your request has been dispatched. '
            'May it glide strong and true through spam filters and '
            'indifference.',
        )

        return super().form_valid(form)


class VoteView(LoginRequiredMixin, CreateView):
    form_class = VoteForm
    template_name = 'vote.html'
    success_url = reverse_lazy('vote:index')

    def get_track_pks(self) -> list[str]:
        track_pks_raw = self.request.GET.get('t')

        if track_pks_raw is None:
            return []

        track_pks = track_pks_raw.split(',')

        if len(track_pks) > settings.MAX_REQUEST_TRACKS:
            raise Http404('too many tracks')

        return track_pks

    def get_tracks(self) -> list[Track]:
        def track_should_be_allowed_for_this_user(track: Track) -> bool:
            return eligible_for(track, self.request.user)

        return list(
            filter(
                track_should_be_allowed_for_this_user,
                (
                    get_object_or_404(Track.objects.public(), pk=pk)
                    for pk in self.get_track_pks()
                ),
            )
        )

    def get_form_kwargs(self) -> dict[str, Any]:
        assert not isinstance(self.request.user, AnonymousUser)
        instance = Vote(user=self.request.user, date=timezone.now())
        return {
            **super().get_form_kwargs(),
            'instance': instance,
            'tracks': self.get_tracks(),
        }

    def form_valid(self, form: VoteForm) -> HttpResponse:
        resp = super().form_valid(form)
        form.instance.tracks.set(self.get_tracks())
        self.request.session['selection'] = []
        return resp

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        tracks = self.get_tracks()
        return {
            **super().get_context_data(**kwargs),
            'tracks': tracks,
        }


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
