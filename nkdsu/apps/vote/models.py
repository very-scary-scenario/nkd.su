from __future__ import annotations

import datetime
import json
import re
from dataclasses import asdict, dataclass
from enum import Enum, auto
from io import BytesIO
from string import ascii_letters
from typing import Any, Iterable, Literal, Optional, cast
from urllib.parse import urlparse
from uuid import uuid4

from Levenshtein import ratio
from PIL import Image, ImageFilter
from dateutil import parser as date_parser
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile
from django.db import models
from django.db.models import Q
from django.template.defaultfilters import slugify
from django.templatetags.static import static
from django.urls import Resolver404, resolve, reverse
from django.utils import timezone
from django.utils.timezone import get_default_timezone
from django_resized import ResizedImageField
from markdown import markdown
import requests
import tweepy

from .managers import NoteQuerySet, TrackQuerySet
from .parsers import ParsedArtist, parse_artist
from .utils import (
    READING_USERNAME,
    assert_never,
    indefinitely,
    lastfm,
    length_str,
    memoize,
    musicbrainzngs,
    pk_cached,
    posting_tw_api,
    reading_tw_api,
    reify,
    split_id3_title,
    vote_url,
)
from ..vote import mixcloud


User = get_user_model()


class CleanOnSaveMixin:
    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class SetShowBasedOnDateMixin:
    show: models.ForeignKey[Show | models.expressions.Combinable, Show]

    def save(self, *args, **kwargs):
        self.show = Show.at(self.date)
        return super().save(*args, **kwargs)


class Show(CleanOnSaveMixin, models.Model):
    """
    A broadcast of the show and, by extention, the week leading up to it.
    """

    showtime = models.DateTimeField(db_index=True)
    end = models.DateTimeField(db_index=True)
    message = models.TextField(blank=True)
    voting_allowed = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.showtime.date().isoformat()

    def __repr__(self) -> str:
        return str(self)

    def clean(self) -> None:
        if self.end < self.showtime:
            raise ValidationError(
                'Show ends before it begins; {end} < {start}'.format(
                    end=self.end, start=self.showtime
                )
            )
        overlap = Show.objects.exclude(pk=self.pk).filter(
            showtime__lt=self.end, end__gt=self.showtime
        )
        if overlap.exists():
            raise ValidationError(
                '{self} overlaps existing shows: {overlap}'.format(
                    self=self, overlap=overlap
                )
            )

    @classmethod
    def current(cls) -> Show:
        """
        Get (or create, if necessary) the show that will next end.
        """

        return cls.at(timezone.now())

    @classmethod
    def _at(cls, time: datetime.datetime, create: bool = True) -> Optional[Show]:
        """
        Get (or create, if necessary) the show for `time`. Use .at() instead.
        """

        existing_show = cls.objects.filter(end__gt=time).order_by('showtime').first()

        if existing_show is not None:
            return existing_show
        elif not create:
            return None
        else:
            # We have to switch to naive and back to make relativedelta
            # look for the local showtime. If we did not, showtime would be
            # calculated against UTC.
            naive_time = timezone.make_naive(time, timezone.get_current_timezone())
            naive_end = naive_time + settings.SHOW_END

            # Work around an unfortunate shortcoming of dateutil where
            # specifying a time on a weekday won't increment the weekday even
            # if our initial time is after that time.
            while naive_end < naive_time:
                naive_time += datetime.timedelta(hours=1)
                naive_end = naive_time + settings.SHOW_END

            naive_showtime = naive_end - settings.SHOWTIME

            our_end = timezone.make_aware(naive_end, timezone.get_current_timezone())
            our_showtime = timezone.make_aware(
                naive_showtime, timezone.get_current_timezone()
            )
            show = cls()
            show.end = our_end
            show.showtime = our_showtime
            show.save()
            return show

    @classmethod
    def at(cls, time: datetime.datetime) -> Show:
        """
        Get the show for the date specified, creating every intervening show
        in the process if necessary.
        """

        all_shows = cls.objects.all()
        if cache.get('all_shows:exists') or all_shows.exists():
            cache.set('all_shows:exists', True, None)
            last_show = all_shows.order_by('-end')[0]
        else:
            this_show = cls._at(time)  # this is the first show!
            assert this_show is not None
            return this_show

        if time <= last_show.end:
            this_show = cls._at(time)
            assert this_show is not None
            return this_show

        show = last_show

        while show.end < time:
            # if create=True, show.next will never return None
            show = cast(Show, show.next(create=True))

        return show

    @memoize
    def broadcasting(self, time: Optional[datetime.datetime] = None) -> bool:
        """
        Return True if the time specified is during this week's show.
        """

        if time is None:
            time = timezone.now()

        return (time >= self.showtime) and (time < self.end)

    @memoize
    @pk_cached(indefinitely)
    def next(self, create: bool = False) -> Optional[Show]:
        """
        Return the next Show.
        """

        return Show._at(self.end + datetime.timedelta(microseconds=1), create)

    @memoize
    @pk_cached(indefinitely)
    def prev(self) -> Optional[Show]:
        """
        Return the previous Show.
        """

        qs = Show.objects.filter(end__lt=self.end)

        try:
            return qs.order_by('-showtime')[0]
        except IndexError:
            return None

    def has_ended(self) -> bool:
        return timezone.now() > self.end

    def _date_kwargs(self, attr: str = 'date') -> dict[str, datetime.datetime]:
        """
        The kwargs you would hand to a queryset to find objects applicable to
        this show. Should not be used unless you're doing something that
        can't use a .show ForeignKey.
        """

        kw = {'%s__lte' % attr: self.end}

        prev_show = self.prev()
        if prev_show is not None:
            kw['%s__gt' % attr] = prev_show.end

        return kw

    @memoize
    def votes(self) -> models.QuerySet[Vote]:
        return self.vote_set.all()

    @memoize
    def plays(self) -> models.QuerySet[Play]:
        return self.play_set.order_by('date').select_related('track')

    @memoize
    def playlist(self) -> list[Track]:
        return [p.track for p in self.plays()]

    @memoize
    def shortlisted(self) -> list[Track]:
        return list(
            filter(
                lambda t: t not in self.playlist(),
                (p.track for p in self.shortlist_set.all()),
            )
        )

    @memoize
    def discarded(self) -> list[Track]:
        return list(
            filter(
                lambda t: t not in self.playlist(),
                (p.track for p in self.discard_set.all()),
            )
        )

    @memoize
    @pk_cached(20)
    def tracks_sorted_by_votes(self) -> list[Track]:
        """
        Return a list of tracks that have been voted for this week, in order of
        when they were last voted for, starting from the most recent.
        """

        track_set = set()
        tracks = []

        votes = (
            Vote.objects.filter(show=self)
            .filter(Q(twitter_user__is_abuser=False) | Q(twitter_user__isnull=True))
            .prefetch_related('tracks')
            .order_by('-date')
        )

        for track in (track for vote in votes for track in vote.tracks.all()):
            if track.pk in track_set:
                continue

            track_set.add(track.pk)
            tracks.append(track)

        return tracks

    @memoize
    @pk_cached(60)
    def revealed(self, show_hidden: bool = False) -> TrackQuerySet:
        """
        Return a all public (unhidden, non-inudesu) tracks revealed in the
        library this week.
        """

        return Track.objects.filter(
            hidden=False, inudesu=False, **self._date_kwargs('revealed')
        )

    @memoize
    @pk_cached(60)
    def cloudcasts(self) -> list[Any]:
        return mixcloud.cloudcasts_for(self.showtime)

    def get_absolute_url(self) -> str:
        if self == Show.current():
            return reverse('vote:index')

        return reverse(
            'vote:show', kwargs={'date': self.showtime.date().strftime('%Y-%m-%d')}
        )

    def get_listen_url(self) -> str:
        return reverse(
            'vote:listen-to-show',
            kwargs={'date': self.showtime.date().strftime('%Y-%m-%d')},
        )

    def get_revealed_url(self) -> str:
        return reverse(
            'vote:added', kwargs={'date': self.showtime.date().strftime('%Y-%m-%d')}
        )

    @reify
    def start(self) -> Optional[datetime.datetime]:
        prev = self.prev()

        if prev is None:
            return None
        else:
            return prev.end

    def api_dict(self, verbose: bool = False) -> dict[str, Any]:
        return {
            'playlist': [p.api_dict() for p in self.plays()],
            'added': [t.api_dict() for t in self.revealed()],
            'votes': [v.api_dict() for v in self.votes()],
            'showtime': self.showtime,
            'finish': self.end,
            'start': self.start,
            'broadcasting': self.broadcasting(),
            'message_markdown': self.message or None,
            'message_html': markdown(self.message) if self.message else None,
            'voting_allowed': self.voting_allowed,
        }

    class Meta:
        ordering = ['-showtime']


class TwitterUser(CleanOnSaveMixin, models.Model):
    class Meta:
        ordering = ['screen_name']

    is_twitteruser = True

    # Twitter stuff
    screen_name = models.CharField(max_length=100)
    user_id = models.BigIntegerField(unique=True)
    name = models.CharField(max_length=100)

    # nkdsu stuff
    is_patron = models.BooleanField(default=False)
    is_abuser = models.BooleanField(default=False)
    updated = models.DateTimeField()

    def __str__(self) -> str:
        return self.screen_name

    def __repr__(self) -> str:
        return self.screen_name

    def twitter_url(self) -> str:
        return 'https://twitter.com/%s' % self.screen_name

    def get_absolute_url(self) -> str:
        return reverse('vote:user', kwargs={'screen_name': self.screen_name})

    def get_toggle_abuser_url(self) -> str:
        return reverse('vote:admin:toggle_abuser', kwargs={'user_id': self.user_id})

    def get_avatar_url(self, try_profile: bool = True) -> str:
        if try_profile and hasattr(self, 'profile'):
            return self.profile.get_avatar_url()
        return static('i/vote-kinds/tweet.png')

    @memoize
    def get_avatar(
        self,
        size: Optional[Literal['original', 'normal']] = None,
        from_cache: bool = True,
    ) -> tuple[str, bytes]:
        ck = f'twav:{size}:{self.pk}'

        if from_cache:
            hit = cache.get(ck)
            if hit:
                return hit

        try:
            url = self.get_twitter_user().profile_image_url_https
        except tweepy.TweepError as e:
            if (e.api_code == 63) or (e.api_code == 50):
                # 63: user is suspended; 50: no such user
                found = finders.find('i/suspended.png')
                if found is None or isinstance(found, list):
                    raise RuntimeError(f'could not find the placeholder image: {found}')
                rv = ('image/png', open(found, 'rb').read())
            else:
                raise
        else:
            if size is not None:
                # `size` here can, I think, also be stuff like '400x400' or whatever,
                # but i'm not sure exactly what the limits are and we're not using any
                # of them anyway, so here's what we support:
                if size != 'original':
                    url_size = '_{}'.format(size)
                else:
                    url_size = ''
                url = re.sub(r'_normal(?=\.[^.]+$)', url_size, url)

            resp = requests.get(url)
            rv = (resp.headers['content-type'], resp.content)

        # update_twitter_avatars will call this every day with
        # from_cache=False, and might sometimes fail, so:
        cache.set(ck, rv, int(60 * 60 * 24 * 2.1))

        return rv

    @memoize
    def votes(self) -> models.QuerySet[Vote]:
        if hasattr(self, 'profile'):
            return self.profile.votes()
        return self.vote_set.order_by('-date').prefetch_related('tracks')

    @memoize
    def votes_with_liberal_preselection(self) -> models.QuerySet[Vote]:
        return self.votes().prefetch_related(
            'show',
            'show__play_set',
            'show__play_set__track',  # doesn't actually appear to work :<
        )

    @memoize
    def votes_for(self, show: Show) -> models.QuerySet[Vote]:
        return self.votes().filter(show=show)

    @memoize
    def tracks_voted_for_for(self, show: Show) -> list[Track]:
        tracks = []
        track_pk_set = set()

        for vote in self.votes_for(show):
            for track in vote.tracks.all():
                if track.pk not in track_pk_set:
                    track_pk_set.add(track.pk)
                    tracks.append(track)

        return tracks

    def _batting_average(
        self,
        cutoff: Optional[datetime.datetime] = None,
        minimum_weight: float = 1,
    ) -> Optional[float]:
        def ba(
            pk, current_show_pk, cutoff: Optional[datetime.datetime]
        ) -> tuple[float, float]:
            score: float = 0
            weight: float = 0

            for vote in self.vote_set.filter(date__gt=cutoff).prefetch_related(
                'tracks'
            ):
                success = vote.success()
                if success is not None:
                    score += success * vote.weight()
                    weight += vote.weight()

            return (score, weight)

        score, weight = ba(self.pk, Show.current().pk, cutoff)

        if weight >= minimum_weight:
            return score / weight
        else:
            # there were no worthwhile votes
            return None

        return score

    @memoize
    def batting_average(self, minimum_weight: float = 1) -> Optional[float]:
        """
        Return a user's batting average for the past six months.
        """

        return self._batting_average(
            cutoff=Show.at(timezone.now() - datetime.timedelta(days=31 * 6)).end,
            minimum_weight=minimum_weight,
        )

    def _streak(self, ls=[]) -> int:
        show = Show.current().prev()
        streak = 0

        while True:
            if show is None:
                return streak
            elif not show.voting_allowed:
                show = show.prev()
            elif show.votes().filter(twitter_user=self).exists():
                streak += 1
                show = show.prev()
            else:
                break

        return streak

    @memoize
    def streak(self) -> int:
        def streak(pk, current_show):
            return self._streak()

        return streak(self.pk, Show.current())

    def all_time_batting_average(self, minimum_weight: float = 1) -> Optional[float]:
        return self._batting_average(minimum_weight=minimum_weight)

    @memoize
    @pk_cached(60 * 60 * 1)
    def get_twitter_user(self) -> tweepy.User:
        return reading_tw_api.get_user(user_id=self.user_id)

    def update_from_api(self) -> None:
        """
        Update this user's database object based on the Twitter API.
        """

        api_user = self.get_twitter_user()

        self.name = api_user.name
        self.screen_name = api_user.screen_name
        self.updated = timezone.now()

        self.save()

    def api_dict(self, verbose: bool = False) -> dict[str, Any]:
        return {
            'user_name': self.name,
            'user_screen_name': self.screen_name,
            'user_image': self.get_avatar_url(),
            'user_id': self.user_id,
        }

    @memoize
    def is_new(self) -> bool:
        return not self.vote_set.exclude(show=Show.current()).exists()

    @memoize
    def is_placated(self) -> bool:
        return self.vote_set.filter(
            tracks__play__show=Show.current(),
            show=Show.current(),
        ).exists()

    @memoize
    def is_shortlisted(self) -> bool:
        return self.vote_set.filter(
            tracks__shortlist__show=Show.current(),
            show=Show.current(),
        ).exists()


def avatar_upload_path(instance: Profile, filename: str) -> str:
    return f"avatars/{instance.user.username}/{uuid4()}.png"


AVATAR_SIZE = 500


class Profile(CleanOnSaveMixin, models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    twitter_user = models.OneToOneField(
        TwitterUser,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name='profile',
    )
    avatar = ResizedImageField(
        upload_to=avatar_upload_path,
        blank=True,
        crop=['middle', 'center'],
        force_format='PNG',
        keep_meta=False,
        size=[AVATAR_SIZE, AVATAR_SIZE],
        help_text=f'will be resized to {AVATAR_SIZE}x{AVATAR_SIZE} and converted to png, so provide that if you can',
        # it'd be nice to optipng these as they're uploaded, but we can always do it later or in a cron job
    )
    display_name = models.CharField(max_length=100, blank=True)

    def __str__(self) -> str:
        return f'{self.display_name} ({self.user.username})'

    def get_absolute_url(self) -> str:
        return reverse("vote:profiles:profile", kwargs={'username': self.user.username})

    def get_avatar_url(self) -> str:
        if self.avatar:
            return self.avatar.url
        elif self.twitter_user:
            return self.twitter_user.get_avatar_url(try_profile=False)
        else:
            return static('i/noise.png')

    @memoize
    def votes(self) -> models.QuerySet[Vote]:
        q = Q(user=self.user)
        if self.twitter_user:
            q = q | Q(twitter_user=self.twitter_user)

        return Vote.objects.filter(q).order_by('-date').prefetch_related('tracks')

    @property
    def is_abuser(self) -> bool:
        return self.twitter_user is not None and self.twitter_user.is_abuser  # XXX make this apply to non-twitter users

    @property
    def name(self) -> str:
        return self.display_name or f'@{self.user.username}'


def art_path(i: Track, f: str) -> str:
    return 'art/bg/%s.%s' % (i.pk, f.split('.')[-1])


def _name_is_related(a: str, b: str) -> bool:
    return (
        (
            # exclude cases where this is a subword match (to avoid matching
            # 'rec' to 'record', for instance):
            # none of these checks matter if b is the longer string or they're
            # the same length
            (len(a) <= len(b))
            or a[len(b)] not in ascii_letters
            or b[-1] not in ascii_letters
        )
        and
        # run our actual comparison
        ratio(a[: len(b)].lower(), b.lower()) > 0.8
    )


class Role:
    anime: Optional[str]
    sortkey_group: float
    caveat: Optional[str] = None
    full_role: str
    kind: str
    specifics: str

    def __init__(self, full_tag: str):
        self.full_tag = full_tag

        result = re.match(
            r'^(?P<anime>.*?) ?\b('
            r'(?P<caveat>rebroadcast )?\b(?P<role>'
            r'((ED|OP)\d*\b[^.]*)|'
            r'((character|image) song\b.*)|'
            r'(ep\d+\b.*)|'
            r'(insert (track|song)\b.*)|'
            r'(ins)|'
            r'((main )?theme ?\d*)|'
            r'(bgm\b.*)|'
            r'(ost)|'
            r'()))$',
            full_tag,
            flags=re.IGNORECASE,
        )

        if result:
            deets = result.groupdict()
            self.anime = deets['anime']
            self.full_role = deets['role']
            self.caveat = deets['caveat']
        else:
            self.anime = None
            self.full_role = self.full_tag

        if self.full_role[:2] in ('OP', 'ED'):
            self.kind, self.specifics = (self.full_role[:2], self.full_role[2:].strip())
        elif self.full_role[:11].lower() == 'insert song':
            self.kind, self.specifics = (
                self.full_role[:11],
                self.full_role[11:].strip(),
            )
        elif ' - ' in self.full_role:
            self.kind, self.specifics = self.full_role.split(' - ', 1)
        elif self.full_role.lower() in ('character song', 'insert song'):
            self.kind, self.specifics = (self.full_role, '')
        else:
            self.kind, self.specifics = ('', self.full_role)

        self.sortkey_group, self.verbose, self.plural = {
            'op': (0, 'Opening theme', 'Opening themes'),
            'ed': (1, 'Ending theme', 'Ending themes'),
            'insert song': (2, 'Insert song', 'Insert songs'),
            'character song': (3, 'Character song', 'Character songs'),
        }.get(self.kind.lower(), (99, 'Other', 'Others'))

        if self.caveat and self.caveat.lower().strip() == 'rebroadcast':
            self.sortkey_group += 0.5

    def __str__(self) -> str:
        return self.full_tag

    def __lt__(self, other) -> bool:
        return self.sortkey() < other.sortkey()

    def __gt__(self, other) -> bool:
        return self.sortkey() > other.sortkey()

    def numbers_in_role(self) -> tuple[int, ...]:
        # basically intended to ensure 'op10' is sorted after 'op9', but also
        # will work perfectly for cases where there's stuff like 'season 3
        # ep10-13'
        return tuple((int(n) for n in re.findall(r'\d+', self.full_role)))

    def sortkey(self) -> tuple[float, str, tuple[int, ...], str]:
        return (
            self.sortkey_group,
            self.kind,
            self.numbers_in_role(),
            self.full_tag,
        )

    def anime_is_related(self, anime: Optional[str]) -> bool:
        if anime is None or self.anime is None:
            return False

        return (len(self.anime) > 1 and len(anime) > 1) and (
            _name_is_related(anime, self.anime) or _name_is_related(self.anime, anime)
        )

    def related_anime(self) -> list[str]:
        return [
            a
            for a in Track.all_anime_titles()
            if a != self.anime and self.anime_is_related(a)
        ]


TrackManager = models.Manager.from_queryset(TrackQuerySet)


class Track(CleanOnSaveMixin, models.Model):
    objects = TrackManager()

    # derived from iTunes
    id = models.CharField(max_length=16, primary_key=True)
    id3_title = models.CharField(max_length=500)
    id3_artist = models.CharField(max_length=5000)
    id3_album = models.CharField(max_length=500, blank=True)
    msec = models.IntegerField(blank=True, null=True)
    added = models.DateTimeField()
    composer = models.CharField(max_length=500, blank=True, db_index=True)
    label = models.CharField(max_length=500, blank=True)
    year = models.IntegerField(blank=True, null=True)

    # nkdsu-specific
    revealed = models.DateTimeField(blank=True, null=True, db_index=True)
    hidden = models.BooleanField()
    inudesu = models.BooleanField()
    background_art = models.ImageField(blank=True, upload_to=art_path)
    metadata_locked = models.BooleanField(default=False)

    def __str__(self) -> str:
        """
        The string that, for instance, would be tweeted
        """

        if self.roles:
            return u'‘%s’ (%s) - %s' % (self.title, self.roles[0], self.artist)
        else:
            return u'‘%s’ - %s' % (self.title, self.artist)

    def __eq__(self, other) -> bool:
        return type(self) == type(other) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    def clean(self) -> None:
        if (not self.inudesu) and (not self.hidden) and (not self.revealed):
            raise ValidationError(
                '{track} is not hidden but has no revealed ' 'date'.format(track=self)
            )

    @classmethod
    def all_anime_titles(cls) -> set[str]:
        return set(
            (
                rd.anime
                for t in cls.objects.public()
                for rd in t.role_details
                if rd.anime is not None
            )
        )

    @classmethod
    def all_artists(cls) -> set[str]:
        return set(a for t in cls.objects.public() for a in t.artist_names())

    @classmethod
    def all_composers(cls) -> set[str]:
        return set(c for t in cls.objects.public() for c in t.composer_names())

    @classmethod
    def all_years(cls) -> list[int]:
        tracks = cls.objects.public().filter(year__isnull=False)

        if settings.DATABASES['default']['ENGINE'] == 'django.db.backends.postgresql':
            return list(
                year  # type: ignore  # we filtered out the null years
                for year in tracks.order_by('year')
                .distinct('year')
                .values_list('year', flat=True)
            )
        else:
            return sorted(
                {
                    year for year in tracks.values_list('year', flat=True)  # type: ignore # same reason as above
                }
            )

    @classmethod
    def complete_decade_range(cls) -> list[tuple[int, bool]]:
        present_years = cls.all_years()
        if not present_years:
            return []

        start_of_earliest_decade = (present_years[0] // 10) * 10

        return [
            (year, year in present_years)
            for year in range(start_of_earliest_decade, present_years[-1] + 1)
        ]

    @classmethod
    def all_decades(cls) -> list[int]:
        return sorted({(year // 10) * 10 for year in cls.all_years()})

    @classmethod
    def suggest_artists(cls, string: str) -> set[str]:
        artist_names = set()
        for track in Track.objects.public().filter(id3_artist__icontains=string):
            for artist_name in track.artist_names():
                artist_names.add(artist_name)

        return artist_names

    @classmethod
    def all_roles(cls, qs: Optional[models.QuerySet[Track]] = None) -> set[str]:
        if qs is None:
            qs = cls.objects.all()

        return set(
            (
                f'{role_detail.full_role}'
                f'\n | {role_detail.kind}\n | {role_detail.specifics}\n'
                for t in qs
                for role_detail in t.role_details
            )
        )

    @classmethod
    def all_non_inudesu_roles(cls) -> set[str]:
        return cls.all_roles(cls.objects.filter(inudesu=False))

    @memoize
    def is_new(self) -> bool:
        return Show.current() == self.show_revealed()

    @memoize
    def show_revealed(self) -> Optional[Show]:
        """
        Return the show that this track was revealed for.
        """

        if self.revealed:
            return Show.at(self.revealed)
        else:
            return None

    def length_str(self) -> str:
        if self.msec is not None:
            return length_str(self.msec)
        else:
            return '-'

    @memoize
    def last_play(self) -> Optional[Play]:
        try:
            return self.play_set.order_by('-date').first()
        except IndexError:
            return None

    @memoize
    def plays(self) -> models.QuerySet[Play]:
        return self.play_set.order_by('date')

    @memoize
    def weeks_since_play(self) -> Optional[int]:
        """
        Get the number of weeks since this track's last Play.
        """

        last_play = self.last_play()
        if last_play is None:
            return None

        show = Show.current()

        return ((show.end - last_play.date).days + 1) // 7

    @reify
    def title(self) -> str:
        return self.split_id3_title()[0]

    @reify
    def album(self) -> str:
        return self.id3_album

    @reify
    def role(self) -> Optional[str]:
        return self.split_id3_title()[1]

    @reify
    def roles(self) -> list[str]:
        return self.role.split('|') if self.role else []

    @reify
    def role_details(self) -> list[Role]:
        return [Role(role) for role in self.roles]

    def role_detail_for_anime(self, anime: str) -> Role:
        self._recently_relevant_anime = anime
        (details,) = [r for r in self.role_details if r.anime == anime]
        return details

    def role_detail_for_recently_relevant_anime(self) -> Role:
        return self.role_detail_for_anime(self._recently_relevant_anime)

    def has_anime(self, anime: str) -> bool:
        return anime in (r.anime for r in self.role_details)

    @reify
    def artist(self) -> str:
        return self.id3_artist

    @memoize
    @pk_cached(90)
    def artists(self) -> ParsedArtist:
        return parse_artist(self.artist)

    def artist_names(self, fail_silently: bool = True) -> Iterable[str]:
        return (
            chunk.text
            for chunk in parse_artist(self.artist, fail_silently=fail_silently).chunks
            if chunk.is_artist
        )

    @memoize
    @pk_cached(90)
    def composers(self) -> ParsedArtist:
        return parse_artist(self.composer)

    def composer_names(self, fail_silently: bool = True) -> Iterable[str]:
        return (
            chunk.text
            for chunk in parse_artist(self.composer, fail_silently=fail_silently).chunks
            if chunk.is_artist
        )

    def split_id3_title(self) -> tuple[str, Optional[str]]:
        return split_id3_title(self.id3_title)

    def eligible(self) -> bool:
        """
        Returns True if this track can be requested.
        """

        return not self.ineligible()

    @memoize
    def ineligible(self) -> Optional[str]:
        """
        Return a string describing why a track is ineligible, or None if it
        is not.
        """

        if self.inudesu:
            return 'inu desu'

        if self.hidden:
            return 'hidden'

        current_show = Show.current()

        if not current_show.voting_allowed:
            return 'no requests allowed this week'

        if self.play_set.filter(show=current_show).exists():
            return 'played this week'

        if self.play_set.filter(show=current_show.prev()).exists():
            return 'played last week'

        block_qs = current_show.block_set.filter(track=self)

        if block_qs.exists():
            return block_qs.get().reason

        return None

    @memoize
    @pk_cached(10)
    def votes_for(self, show: Show) -> models.QuerySet[Vote]:
        """
        Return votes for this track for a given show.
        """

        return self.vote_set.filter(show=show).order_by('date')

    @memoize
    def notes(self) -> models.QuerySet[Note]:
        return self.note_set.for_show_or_none(Show.current())

    @memoize
    def public_notes(self) -> models.QuerySet[Note]:
        return self.notes().filter(public=True)

    def play(self, tweet: bool = True) -> Play:
        """
        Mark this track as played.
        """

        play = Play(
            track=self,
            date=timezone.now(),
        )

        play.save()

        if tweet:
            play.tweet()

        return play

    play.alters_data = True  # type: ignore

    def shortlist(self) -> None:
        shortlist = Shortlist(
            track=self,
            show=Show.current(),
        )
        shortlist.take_first_available_index()

        try:
            shortlist.save()
        except ValidationError:
            pass

    shortlist.alters_data = True  # type: ignore

    def discard(self) -> None:
        try:
            Discard(
                track=self,
                show=Show.current(),
            ).save()
        except ValidationError:
            pass

    discard.alters_data = True  # type: ignore

    def reset_shortlist_discard(self) -> None:
        qs_kwargs = {'track': self, 'show': Show.current()}
        Discard.objects.filter(**qs_kwargs).delete()
        Shortlist.objects.filter(**qs_kwargs).delete()

    reset_shortlist_discard.alters_data = True  # type: ignore

    def hide(self) -> None:
        self.hidden = True
        self.save()

    hide.alters_data = True  # type: ignore

    def unhide(self) -> None:
        self.hidden = False

        if not self.revealed:
            self.revealed = timezone.now()

        self.save()

    unhide.alters_data = True  # type: ignore

    def lock_metadata(self) -> None:
        self.metadata_locked = True
        self.save()

    lock_metadata.alters_data = True  # type: ignore

    def unlock_metadata(self) -> None:
        self.metadata_locked = False
        self.save()

    unlock_metadata.alters_data = True  # type: ignore

    def slug(self) -> str:
        return slugify(self.title)

    def get_absolute_url(self) -> str:
        return reverse('vote:track', kwargs={'slug': self.slug(), 'pk': self.pk})

    def get_public_url(self) -> str:
        return settings.SITE_URL + self.get_absolute_url()

    def get_report_url(self) -> str:
        return reverse('vote:report', kwargs={'pk': self.pk})

    def get_vote_url(self) -> str:
        """
        Return the url for voting for this track alone.
        """

        return vote_url([self])

    def get_lastfm_track(self) -> dict[str, Any]:
        return lastfm(
            method='track.getInfo',
            track=self.title,
            artist=self.artist,
        ).get('track')

    @memoize
    @pk_cached(3600)
    def musicbrainz_release(self) -> Optional[dict[str, Any]]:
        releases = musicbrainzngs.search_releases(
            tracks=self.title,
            release=self.album,
            artist=self.artist,
        ).get('release-list')

        official_releases = [r for r in releases if r.get('status') == 'Official']

        if official_releases:
            return official_releases[0]
        elif releases:
            return releases[0]
        else:
            return None

    def _get_lastfm_album_from_album_tag(self) -> Optional[dict[str, Any]]:
        return lastfm(
            method='album.getInfo',
            artist=self.artist,
            album=self.album,
        ).get('album')

    def _get_lastfm_album_from_musicbrainz_release(self) -> Optional[dict[str, Any]]:
        release = self.musicbrainz_release()

        if release is not None:
            return lastfm(
                method='album.getInfo',
                artist=release['artist-credit-phrase'],
                album=release['title'],
            ).get('album')
        else:
            return None

    def _get_lastfm_album_from_track_tag(self) -> Optional[dict[str, Any]]:
        track = self.get_lastfm_track()

        if track is not None:
            return track.get('album')

    def get_lastfm_album(self) -> Optional[dict[str, Any]]:
        album = self._get_lastfm_album_from_album_tag()

        if album is not None:
            return album
        else:
            return self._get_lastfm_album_from_track_tag()

    def get_lastfm_artist(self) -> Optional[dict[str, Any]]:
        return lastfm(method='artist.getInfo', artist=self.artist).get('artist')

    def get_biggest_lastfm_image_url(self) -> Optional[str]:
        for getter in [
            self._get_lastfm_album_from_album_tag,
            self._get_lastfm_album_from_track_tag,
            self.get_lastfm_artist,
            self._get_lastfm_album_from_musicbrainz_release,
        ]:
            thing = getter()

            if thing is None:
                continue

            images = thing.get('image')

            if images is None:
                continue

            image_url = images[-1]['#text']

            if image_url and not image_url.endswith('lastfm_wrongtag.png'):
                return image_url
        else:
            return None

    def update_background_art(self) -> None:
        image_url = self.get_biggest_lastfm_image_url()

        if image_url is None:
            self.background_art = None
            self.save()
            return

        try:
            input_image = Image.open(BytesIO(requests.get(image_url).content))
        except IOError as e:
            print('{}:\n - {}'.format(self, e))
            self.background_art = None
            self.save()
            return

        if input_image.mode not in ['L', 'RGB']:
            input_image = input_image.convert('RGB')

        # in almost all circumstances, it will be width that determines display
        # size, so we should set our blur radius relative to that.
        radius = input_image.size[0] / 130

        blurred = input_image.filter(ImageFilter.GaussianBlur(radius=radius))

        suffix = '.jpg'
        temp_file = NamedTemporaryFile(delete=True, suffix=suffix)
        blurred.save(temp_file, 'JPEG', quality=60)

        temp_file.flush()

        self.background_art.save(image_url.split('/')[-1] + suffix, File(temp_file))

    def api_dict(self, verbose: bool = False) -> dict[str, Any]:
        show_revealed = self.show_revealed()

        the_track = {
            'id': self.id,
            'title': self.title,
            'role': self.role,
            'role_parsed': [
                {
                    'anime': role.anime,
                    'kind': role.kind,
                    'specifics': role.specifics,
                }
                for role in self.role_details
            ],
            'artist': self.artist,
            'artists': list(self.artist_names()),
            'artists_parsed': [asdict(a) for a in self.artists().chunks],
            'eligible': self.eligible(),
            'ineligibility_reason': self.ineligible() or None,
            'length': self.msec,
            'inu desu': self.inudesu,
            'added_week': show_revealed.showtime.date().strftime('%Y-%m-%d')
            if show_revealed is not None
            else None,
            'added': self.added.isoformat(),
            'url': self.get_public_url(),
            'background': (self.background_art.url if self.background_art else None),
        }

        if verbose:
            the_track.update({'plays': [p.date for p in self.plays()]})

        return the_track


MANUAL_VOTE_KINDS = (
    ('email', 'email'),
    ('discord', 'discord'),
    ('text', 'text'),
    ('tweet', 'tweet'),
    ('person', 'in person'),
    ('phone', 'on the phone'),
)


class VoteKind(Enum):
    #: A request made using the website's built-in requesting machinery
    local = auto()

    #: A request derived from a tweet
    twitter = auto()

    #: A request manually created by an admin to reflect, for example, an email
    manual = auto()


class Vote(SetShowBasedOnDateMixin, CleanOnSaveMixin, models.Model):
    # universal
    tracks = models.ManyToManyField(Track, db_index=True)
    date = models.DateTimeField(db_index=True)
    show = models.ForeignKey(Show, related_name='vote_set', on_delete=models.CASCADE)
    text = models.TextField(
        blank=True,
        max_length=280,
        help_text='A comment to be shown alongside your request',
    )

    # local only
    user = models.ForeignKey(
        User, blank=True, null=True, db_index=True, on_delete=models.SET_NULL
    )

    # twitter only
    twitter_user = models.ForeignKey(
        TwitterUser, blank=True, null=True, db_index=True, on_delete=models.SET_NULL
    )
    tweet_id = models.BigIntegerField(blank=True, null=True)

    # manual only
    name = models.CharField(max_length=40, blank=True)
    kind = models.CharField(max_length=10, choices=MANUAL_VOTE_KINDS, blank=True)

    @classmethod
    def handle_tweet(cls, tweet) -> Optional[Vote]:
        """
        Take a tweet json object and create, save and return the vote it has
        come to represent (or None if it's not a valid vote).
        """

        text = tweet.get('full_text', None) or tweet.get('text', None)

        if text is None:
            if 'delete' in tweet:
                Vote.objects.filter(tweet_id=tweet['delete']['status']['id']).delete()
            return None

        if cls.objects.filter(tweet_id=tweet['id']).exists():
            return None  # we already have this tweet

        created_at = date_parser.parse(tweet['created_at'])

        def mention_is_first_and_for_us(mention):
            return (
                mention['indices'][0] == 0
                and mention['screen_name'] == READING_USERNAME
            )

        if not any(
            [mention_is_first_and_for_us(m) for m in tweet['entities']['user_mentions']]
        ):
            return None

        show = Show.at(created_at)

        user_qs = TwitterUser.objects.filter(user_id=tweet['user']['id'])
        try:
            twitter_user = user_qs.get()
        except TwitterUser.DoesNotExist:
            twitter_user = TwitterUser(
                user_id=tweet['user']['id'],
            )

        twitter_user.screen_name = tweet['user']['screen_name']
        twitter_user.name = tweet['user']['name']
        twitter_user.updated = created_at
        twitter_user.save()

        tracks = []
        for url in (tweet.get('extended_entities') or tweet.get('entities', {})).get(
            'urls', ()
        ):
            parsed = urlparse(url['expanded_url'])

            try:
                match = resolve(parsed.path)
            except Resolver404:
                continue

            if match.namespace == 'vote' and match.url_name == 'track':
                track_qs = Track.objects.public().filter(pk=match.kwargs['pk'])

                try:
                    track = track_qs.get()
                except Track.DoesNotExist:
                    continue

                if (
                    track.pk
                    not in (t.pk for t in twitter_user.tracks_voted_for_for(show))
                    and track.eligible()
                ):
                    tracks.append(track)

        if tracks:
            vote = cls(
                tweet_id=tweet['id'],
                twitter_user=twitter_user,
                date=created_at,
                text=text,
            )

            vote.save()

            for track in tracks:
                vote.tracks.add(track)

            vote.save()
            return vote
        else:
            return None

    def clean(self) -> None:
        match self.vote_kind:
            case VoteKind.twitter:
                if self.tweet_id or self.twitter_user_id:
                    raise ValidationError('Twitter attributes present on manual vote')
                if self.user:
                    raise ValidationError('Local attributes present on manual vote')
                if not (self.name and self.kind):
                    raise ValidationError('Attributes missing from manual vote')
                return
            case VoteKind.manual:
                if self.name or self.kind:
                    raise ValidationError('Manual attributes present on Twitter vote')
                if self.user:
                    raise ValidationError('Local attributes present on Twitter vote')
                if not (self.tweet_id and self.twitter_user_id):
                    raise ValidationError(
                        'Twitter attributes missing from Twitter vote'
                    )
                return
            case VoteKind.local:
                if self.name or self.kind:
                    raise ValidationError('Manual attributes present on local vote')
                if self.tweet_id or self.twitter_user_id:
                    raise ValidationError('Twitter attributes present on local vote')
                if not self.user:
                    raise ValidationError('No user specified for local vote')
                return

        assert_never(self.vote_kind)

    def either_name(self) -> str:
        if self.name:
            return self.name
        assert self.twitter_user is not None
        return '@{0}'.format(self.twitter_user.screen_name)

    @property
    def vote_kind(self) -> VoteKind:
        if self.tweet_id:
            return VoteKind.twitter
        elif self.kind:
            return VoteKind.manual
        else:
            return VoteKind.local

    @property
    def is_twitter(self) -> bool:
        return self.vote_kind == VoteKind.twitter

    @property
    def is_manual(self) -> bool:
        return self.vote_kind == VoteKind.manual

    @property
    def is_local(self) -> bool:
        return self.vote_kind == VoteKind.local

    def get_image_url(self) -> str:
        if self.user and self.user.profile:
            return self.user.profile.get_avatar_url()
        elif self.twitter_user:
            return self.twitter_user.get_avatar_url()
        elif self.vote_kind == VoteKind.manual:
            return static('i/vote-kinds/{0}.png'.format(self.kind))
        else:
            return static('i/noise.png')

    def __str__(self) -> str:
        tracks = u', '.join([t.title for t in self.tracks.all()])

        return u'{user} at {date} for {tracks}'.format(
            user=self.name or self.twitter_user,
            date=self.date,
            tracks=tracks,
        )

    @memoize
    def content(self) -> str:
        """
        Return the non-mention, non-url content of the text.
        """

        content = self.text

        if self.vote_kind == VoteKind.twitter:
            while content.lower().startswith('@{}'.format(READING_USERNAME).lower()):
                content = content.split(' ', 1)[1]

            content = content.strip('- ')

            for word in content.split():
                if re.match(r'https?://[^\s]+', word):
                    content = content.replace(word, '').strip()
                elif len(word) == 16 and re.match('[0-9A-F]{16}', word):
                    # for the sake of old pre-url votes
                    content = content.replace(word, '').strip()

        return content

    @memoize
    def birthday(self) -> bool:
        content = self.content()
        return bool(
            content and re.search(r'\b(birthday|b-?day)', content, flags=re.IGNORECASE)
        )

    @reify
    def hat(self) -> Optional[UserBadge]:
        """
        Get the most important badge for a given vote, where the most important
        badge is the last one defined in `BADGES`.
        """

        badge_order = [b.slug for b in BADGES]

        if not self.twitter_user:
            return None

        for badge in sorted(
            (
                b
                for b in self.twitter_user.userbadge_set.all()
                if (
                    b.badge_info['start'] is None
                    or b.badge_info['start'] <= self.show.end
                )
                and (
                    b.badge_info['finish'] is None
                    or b.badge_info['finish'] >= self.show.end
                )
            ),
            key=lambda b: badge_order.index(b.badge),
            reverse=True,
        ):
            return badge

        return None

    @memoize
    @pk_cached(indefinitely)
    def success(self) -> Optional[float]:
        """
        Return how successful this vote is, as a float between 0 and 1, or None
        if we don't know yet.
        """

        if not self.show.has_ended():
            return None

        successes = 0
        for track in self.tracks.all():
            if track in self.show.playlist():
                successes += 1

        return successes / self.weight()

    @memoize
    @pk_cached(indefinitely)
    def weight(self) -> float:
        """
        Return how much we should take this vote into account when calculating
        a user's batting average.
        """

        return float(self.tracks.all().count())

    def api_dict(self, verbose: bool = False) -> dict[str, Any]:
        tracks = self.tracks.all()
        the_vote: dict[str, Any] = {
            'comment': self.content() if self.content() != '' else None,
            'time': self.date,
            'track_ids': [t.id for t in tracks],
            'tracks': [t.api_dict() for t in tracks],
        }

        if self.twitter_user is not None and self.tweet_id is not None:
            the_vote.update({'tweet_id': self.tweet_id})
            the_vote.update(self.twitter_user.api_dict())

        return the_vote

    def twitter_url(self) -> Optional[str]:
        if self.twitter_user is None or self.tweet_id is None:
            return None

        return 'https://twitter.com/%s/status/%s/' % (
            self.twitter_user.screen_name,
            self.tweet_id,
        )


class Play(SetShowBasedOnDateMixin, CleanOnSaveMixin, models.Model):
    date = models.DateTimeField(db_index=True)
    show = models.ForeignKey(Show, on_delete=models.CASCADE)
    track = models.ForeignKey(Track, db_index=True, on_delete=models.CASCADE)
    tweet_id = models.BigIntegerField(blank=True, null=True)

    def __str__(self):
        return u'%s at %s' % (self.track, self.date)

    def clean(self) -> None:
        for play in self.show.play_set.all():
            if play != self and play.track == self.track:
                raise ValidationError(
                    '{track} already played during {show}.'.format(
                        track=self.track, show=self.show
                    )
                )

    def save(self, *args, **kwargs) -> None:
        super().save(*args, **kwargs)

        if self.track.hidden:
            self.track.hidden = False
            self.track.revealed = timezone.now()
            self.track.save()

    def get_tweet_text(self) -> str:
        # here we add a zwsp after every . to prevent twitter from turning
        # things into links
        delinked_name = str(self.track).replace('.', '.\u200b')

        status = f'Now playing on {settings.HASHTAG}: {delinked_name}'

        if len(status) > settings.TWEET_LENGTH:
            # twitter counts ellipses as two characters for some reason, so we get rid of two:
            status = status[: settings.TWEET_LENGTH - 2].strip() + '…'

        return status

    def tweet(self) -> None:
        """
        Send out a tweet for this play, set self.tweet_id and save.
        """

        if self.tweet_id is not None:
            raise TypeError('This play has already been tweeted')

        tweet = posting_tw_api.update_status(self.get_tweet_text())
        self.tweet_id = tweet.id
        self.save()

    tweet.alters_data = True  # type: ignore

    def api_dict(self, verbose: bool = False) -> dict[str, Any]:
        return {
            'time': self.date,
            'track': self.track.api_dict(),
        }


class Block(CleanOnSaveMixin, models.Model):
    """
    A particular track that we are not going to allow to be voted for on
    particular show.
    """

    track = models.ForeignKey(Track, on_delete=models.CASCADE)
    reason = models.CharField(max_length=256)
    show = models.ForeignKey(Show, on_delete=models.CASCADE)

    class Meta:
        unique_together = [['show', 'track']]


class Shortlist(CleanOnSaveMixin, models.Model):
    show = models.ForeignKey(Show, on_delete=models.CASCADE)
    track = models.ForeignKey(Track, on_delete=models.CASCADE)
    index = models.IntegerField(default=0)

    class Meta:
        unique_together = [['show', 'track'], ['show', 'index']]
        ordering = ['-show__showtime', 'index']

    def take_first_available_index(self) -> None:
        existing = Shortlist.objects.filter(show=self.show)

        if not existing.exists():
            self.index = 0
        else:
            for index, shortlist in enumerate(existing):
                if shortlist.index != index:
                    shortlist.index = index
                    shortlist.save()

            self.index = index + 1


class Discard(CleanOnSaveMixin, models.Model):
    """
    A track that we're not going to play, but that we don't want to make public
    that we're not going to play.
    """

    show = models.ForeignKey(Show, on_delete=models.CASCADE)
    track = models.ForeignKey(Track, on_delete=models.CASCADE)

    class Meta:
        unique_together = [['show', 'track']]


class Request(CleanOnSaveMixin, models.Model):
    """
    A request for a database addition.
    """

    METADATA_KEYS = ['trivia', 'trivia_question', 'contact']

    created = models.DateTimeField(auto_now_add=True)
    successful = models.BooleanField()
    blob = models.TextField()
    filled = models.DateTimeField(blank=True, null=True)
    filled_by = models.ForeignKey(
        User, blank=True, null=True, on_delete=models.SET_NULL
    )
    claimant = models.ForeignKey(
        User, blank=True, null=True, related_name='claims', on_delete=models.SET_NULL
    )
    track = models.ForeignKey(Track, blank=True, null=True, on_delete=models.SET_NULL)

    def serialise(self, struct):
        self.blob = json.dumps(struct)

    def struct(self):
        return json.loads(self.blob)

    def non_metadata(self):
        return {
            k: v
            for k, v in self.struct().items()
            if (k not in Request.METADATA_KEYS or k == 'contact') and v.strip()
        }

    class Meta:
        ordering = ['-created']


NoteManager = models.Manager.from_queryset(NoteQuerySet)


class Note(CleanOnSaveMixin, models.Model):
    """
    A note about whatever for a particular track.
    """

    objects = NoteManager()

    track = models.ForeignKey(Track, on_delete=models.CASCADE)
    show = models.ForeignKey(Show, blank=True, null=True, on_delete=models.CASCADE)
    public = models.BooleanField(default=False)
    content = models.TextField()

    def __str__(self) -> str:
        return self.content


@dataclass
class Badge:
    slug: str
    description_fmt: str
    summary: str
    icon: str
    url: str
    start: Optional[datetime.datetime]
    finish: Optional[datetime.datetime]

    def info(self, user: TwitterUser) -> dict[str, Any]:
        return {
            'slug': self.slug,
            'description': self.description_fmt.format(user=user),
            'summary': self.summary,
            'icon': self.icon,
            'url': self.url,
            'start': Show.at(self.start).showtime if self.start is not None else None,
            'finish': Show.at(self.finish).end if self.finish is not None else None,
        }


BADGES: list[Badge] = [
    Badge(
        'tblc',
        u'{user.name} bought Take Back Love City for the RSPCA.',
        'put up with bad music for animals',
        'headphones',
        'https://desus.bandcamp.com/album/take-back-love-city',
        None,
        datetime.datetime(1990, 1, 1, tzinfo=get_default_timezone()),
    ),
    Badge(
        'charity-2016',
        u'{user.name} donated to the Very Scary Scenario charity streams for '
        u'Special Effect in 2016.',
        'likes fun, hates exclusion',
        'heart',
        'https://www.justgiving.com/fundraising/very-scary-scenario',
        datetime.datetime(2016, 10, 15, tzinfo=get_default_timezone()),
        datetime.datetime(2016, 11, 15, tzinfo=get_default_timezone()),
    ),
    Badge(
        'charity-2017',
        u'{user.name} donated to the Very Scary Scenario charity streams and '
        u'Neko Desu All-Nighter for Cancer Research UK in 2017.',
        'likes depriving people of sleep, hates cancer',
        'heart',
        'https://www.justgiving.com/fundraising/very-charity-scenario-2017',
        datetime.datetime(2017, 10, 1, tzinfo=get_default_timezone()),
        datetime.datetime(2017, 11, 27, tzinfo=get_default_timezone()),
    ),
    Badge(
        'charity-2018',
        u'{user.name} donated to the Very Scary Scenario charity streams for '
        u'Cancer Research UK in 2018.',
        'likes depriving people of sleep, hates cancer',
        'medkit',
        'https://www.justgiving.com/fundraising/very-charity-scenario-2018',
        datetime.datetime(2018, 10, 1, tzinfo=get_default_timezone()),
        datetime.datetime(2018, 11, 27, tzinfo=get_default_timezone()),
    ),
    Badge(
        'charity-2019',
        u'{user.name} donated to the Very Scary Scenario charity streams for '
        u'Samaritans in 2019.',
        'likes depriving people of sleep, fan of good mental health',
        'life-ring',
        'https://www.justgiving.com/fundraising/very-charity-scenario-2019',
        datetime.datetime(2019, 10, 1, tzinfo=get_default_timezone()),
        datetime.datetime(2019, 11, 27, tzinfo=get_default_timezone()),
    ),
    Badge(
        'charity-2020',
        u'{user.name} donated to the Very Scary Scenario charity streams for '
        u'Cancer Research UK in 2020.',
        'donated to the 2020 Very Scary Scenario charity streams',
        'heartbeat',
        'https://www.justgiving.com/fundraising/very-charity-scenario-2020',
        datetime.datetime(2020, 10, 1, tzinfo=get_default_timezone()),
        datetime.datetime(2020, 11, 27, tzinfo=get_default_timezone()),
    ),
    Badge(
        'charity-2021',
        u'{user.name} donated to the Very Scary Scenario charity streams for '
        u'Mind in 2021.',
        'donated to the 2021 Very Scary Scenario charity streams',
        'brain',
        'https://www.justgiving.com/fundraising/very-charity-scenario-2021',
        datetime.datetime(2021, 10, 9, tzinfo=get_default_timezone()),
        datetime.datetime(2021, 11, 27, tzinfo=get_default_timezone()),
    ),
    Badge(
        'charity-2022',
        u'{user.name} donated to the Very Scary Scenario charity streams for '
        u'akt in 2022.',
        'donated to the 2022 Very Scary Scenario charity streams',
        'home',
        'https://www.justgiving.com/fundraising/very-charity-scenario-2022',
        datetime.datetime(2022, 10, 9, tzinfo=get_default_timezone()),
        datetime.datetime(2022, 11, 27, tzinfo=get_default_timezone()),
    ),
]


class UserBadge(CleanOnSaveMixin, models.Model):
    badge = models.CharField(
        choices=[(b.slug, b.description_fmt) for b in BADGES],
        max_length=max((len(b.slug) for b in BADGES)),
    )
    user = models.ForeignKey(TwitterUser, on_delete=models.CASCADE)

    @reify
    def badge_info(self) -> dict[str, Any]:
        (badge,) = (b for b in BADGES if b.slug == self.badge)
        return badge.info(self.user)

    class Meta:
        unique_together = [['badge', 'user']]
