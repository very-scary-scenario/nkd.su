from __future__ import annotations

import datetime
import json
import re
from dataclasses import asdict, dataclass
from enum import Enum, auto
from functools import cached_property
from io import BytesIO
from string import ascii_letters
from typing import Any, Iterable, Literal, Optional, TYPE_CHECKING, TypedDict, cast
from urllib.parse import quote, urlparse
from uuid import uuid4

from Levenshtein import ratio
from PIL import Image, ImageFilter
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile
from django.db import models
from django.db.models import Q
from django.db.models.constraints import CheckConstraint, UniqueConstraint
from django.template.defaultfilters import slugify
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone
from django.utils.timezone import get_default_timezone
from django_resized import ResizedImageField
from markdown import markdown
import requests

from .anime import Anime, get_anime
from .api_utils import JsonDict, Serializable
from .managers import NoteQuerySet, TrackQuerySet
from .mastodon_instances import MASTODON_INSTANCES
from .parsers import ParsedArtist, parse_artist
from .placeholder_avatars import placeholder_avatar_for
from .utils import (
    READING_USERNAME,
    assert_never,
    cached,
    indefinitely,
    lastfm,
    length_str,
    memoize,
    musicbrainzngs,
    pk_cached,
    split_id3_title,
    vote_edit_cutoff,
    vote_url,
)
from .voter import Voter
from ..vote import mixcloud


if TYPE_CHECKING:
    from django.db.models.fields.manager import RelatedManager


User = get_user_model()

MAX_WEBSITES = 5


class CleanOnSaveMixin:
    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class SetShowBasedOnDateMixin:
    show: models.ForeignKey[Show | models.expressions.Combinable, Show]

    def save(self, *args, **kwargs):
        self.show = Show.at(self.date)
        return super().save(*args, **kwargs)


class Show(CleanOnSaveMixin, Serializable, models.Model):
    """
    A broadcast of the show and, by extention, the week leading up to it.
    """

    class Meta:
        constraints = [
            models.UniqueConstraint('showtime', name='unique_showtime'),
        ]
        ordering = ['-showtime']

    showtime = models.DateTimeField(db_index=True)
    end = models.DateTimeField(db_index=True)
    message = models.TextField(blank=True)
    voting_allowed = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.showtime.date().isoformat()

    def __repr__(self) -> str:
        return str(self)

    def __hash__(self) -> int:
        return hash((type(self), self.id))

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
    @cached(2, 'vote:models:Show:current')
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
        Return :data:`True` if the time specified is during this week's show.
        """

        if time is None:
            time = timezone.now()

        return (time >= self.showtime) and (time < self.end)

    @memoize
    @pk_cached(indefinitely)
    def next(self, create: bool = False) -> Optional[Show]:
        """
        Return the :class:`Show` chronologically after that one.
        """

        return Show._at(self.end + datetime.timedelta(microseconds=1), create)

    @memoize
    @pk_cached(indefinitely)
    def prev(self) -> Optional[Show]:
        """
        Return the :class:`Show` chronologically before that one.
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
        playlist = self.playlist()
        return [p.track for p in self.shortlist_set.all() if p.track not in playlist]

    @memoize
    def discarded(self) -> list[Track]:
        playlist = self.playlist()
        return [p.track for p in self.discard_set.all() if p.track not in playlist]

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
            .filter(Q(user__profile__is_abuser=False) | Q(user__isnull=True))
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
        Return all public (unhidden, non-inudesu) tracks revealed in the
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

    @cached_property
    def start(self) -> Optional[datetime.datetime]:
        prev = self.prev()

        if prev is None:
            return None
        else:
            return prev.end

    def api_dict(self, verbose: bool = False) -> JsonDict:
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


class TwitterUser(Voter, CleanOnSaveMixin, models.Model):
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

    def __hash__(self) -> int:
        return hash((type(self), self.id))

    @property
    def username(self) -> str:
        return self.screen_name

    def _twitter_user_and_profile(
        self,
    ) -> tuple[Optional[TwitterUser], Optional[Profile]]:
        return (self, getattr(self, 'profile', None))

    def twitter_url(self) -> str:
        return 'https://twitter.com/%s' % self.screen_name

    def get_absolute_url(self) -> str:
        return reverse('vote:user', kwargs={'screen_name': self.screen_name})

    def get_toggle_abuser_url(self) -> str:
        return reverse(
            'vote:admin:toggle_twitter_abuser', kwargs={'user_id': self.user_id}
        )

    def get_avatar_url(self, try_profile: bool = True) -> str:
        if try_profile and hasattr(self, 'profile'):
            return self.profile.get_avatar_url()
        return static(placeholder_avatar_for(self))

    @memoize
    def unordered_votes(self) -> models.QuerySet[Vote]:
        if hasattr(self, 'profile'):
            return self.profile.votes()
        return self.vote_set.all()

    def api_dict(self, verbose: bool = False) -> JsonDict:
        return {
            'user_name': self.name,
            'user_screen_name': self.screen_name,
            'user_image': self.get_avatar_url(),
            'user_id': self.user_id,
        }


def avatar_upload_path(instance: Profile, filename: str) -> str:
    return f"avatars/{instance.user.username}/{uuid4()}.png"


AVATAR_SIZE = 500


class Profile(Voter, CleanOnSaveMixin, models.Model):
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
        help_text=(
            f'will be resized to {AVATAR_SIZE}x{AVATAR_SIZE} and converted to png, so'
            ' provide that if you can'
        ),
        # it'd be nice to optipng these as they're uploaded, but we can always do it later or in a cron job
    )
    display_name = models.CharField(max_length=100, blank=True)

    is_patron = models.BooleanField(default=False)
    is_abuser = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f'{self.display_name} ({self.user.username})'

    def __hash__(self) -> int:
        return hash((type(self), self.id))

    def _twitter_user_and_profile(
        self,
    ) -> tuple[Optional[TwitterUser], Optional[Profile]]:
        return (self.twitter_user, self)

    @property
    def username(self) -> str:
        return self.user.username

    def get_absolute_url(self) -> str:
        return reverse("vote:profiles:profile", kwargs={'username': self.user.username})

    def get_avatar_url(self) -> str:
        if self.avatar:
            return self.avatar.url
        elif self.twitter_user:
            return self.twitter_user.get_avatar_url(try_profile=False)
        else:
            return static(placeholder_avatar_for(self))

    @memoize
    def unordered_votes(self) -> models.QuerySet[Vote]:
        q = Q(user=self.user)
        if self.twitter_user:
            q = q | Q(twitter_user=self.twitter_user)

        return Vote.objects.filter(q)

    @property  # type: ignore[override]
    def name(self) -> str:
        return self.display_name or f'@{self.user.username}'

    @name.setter
    def name(self, name: str) -> None:
        self.display_name = name

    def get_toggle_abuser_url(self) -> str:
        return reverse('vote:admin:toggle_local_abuser', kwargs={'user_id': self.pk})

    def has_max_websites(self) -> bool:
        return self.websites.count() >= MAX_WEBSITES

    def get_websites(self) -> Iterable[UserWebsite]:
        return sorted(self.websites.all(), key=lambda w: (w.kind, w.url))


UserWebsiteKind = Literal[
    '_website',
    'anilist',
    'bsky',
    'cohost',
    'facebook',
    'instagram',
    'linkedin',
    'mastodon',
    'myanimelist',
    'nkdsu',
    'threads',
    'tumblr',
    'twitch',
    'twitter',
    'x',
    'youtube',
]


class UserWebsite(CleanOnSaveMixin, models.Model):
    class Meta:
        constraints = [
            UniqueConstraint(
                fields=['url', 'profile'],
                name='unique_url_per_profile',
                violation_error_message="You can't provide the same URL more than once",
            ),
        ]

    url = models.URLField()
    profile = models.ForeignKey(
        Profile, related_name='websites', on_delete=models.CASCADE
    )

    def clean(self) -> None:
        super().clean()
        if self._state.adding and self.profile.websites.count() >= MAX_WEBSITES:
            raise ValidationError('You cannot have any more websites')

    @property
    def kind(self) -> UserWebsiteKind:
        """
        Return an appropriate identify for for what kind of URL this is.

        >>> UserWebsite(url='https://someone.tumblr.com').kind
        'tumblr'
        >>> UserWebsite(url='https://tumblr.com/someone').kind
        'tumblr'
        >>> UserWebsite(url='https://cohost.org/someone').kind
        'cohost'
        >>> UserWebsite(url='https://www.instagram.com/someone').kind
        'instagram'
        >>> UserWebsite(url='https://plush.city/@someone').kind
        'mastodon'
        >>> UserWebsite(url='https://website.tld').kind
        '_website'
        """

        hostname = urlparse(self.url).hostname
        assert hostname is not None, f"url {self.url!r} has no hostname"

        basic_kinds: dict[str, UserWebsiteKind] = {
            'anilist.co': 'anilist',
            'bsky.app': 'bsky',
            'cohost.org': 'cohost',
            'facebook.com': 'facebook',
            'instagram.com': 'instagram',
            'linkedin.com': 'linkedin',
            'myanimelist.net': 'myanimelist',
            'nkd.su': 'nkdsu',
            'threads.net': 'threads',
            'tumblr.com': 'tumblr',
            'twitch.tv': 'twitch',
            'twitter.com': 'twitter',
            'x.com': 'x',
            'youtube.com': 'youtube',
        }
        rv = basic_kinds.get(hostname.removeprefix('www.'))

        if rv is not None:
            return rv

        # some places let you use subdomains:
        if hostname.endswith('.tumblr.com'):
            return 'tumblr'
        if hostname.endswith('.cohost.com'):
            return 'cohost'

        if hostname in MASTODON_INSTANCES:
            return 'mastodon'

        return '_website'


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
    kind: str = ''
    specifics: str = ''

    def __init__(self, full_tag: str):
        self.full_tag = full_tag

        ep = r'(ep\d+(-\d+)?\b.*)'
        result = re.match(
            r'^(?P<anime>.*?) ?\b('
            r'(?P<caveat>(rebroadcast|tv broadcast|netflix) )?\b(?P<role>'
            r'(('
            r'((ED|OP))|'
            r'(insert (track|song)\b)|'
            + ep
            + r')(?P<specifics>\d*\b\W*\w* ?('
            + ep
            + r'|b-side)?)?)|'
            r'((character|image) song\b.*)|'
            r'(ins)|'
            r'((main )?theme ?\d*)|'
            r'(bgm\b.*)|'
            r'(ost)|'
            r'()))$',
            full_tag,
            flags=re.IGNORECASE,
        )

        if result and result.groupdict()['role'] and result.groupdict()['anime']:
            deets = result.groupdict()
            self.anime = deets['anime']
            self.full_role = deets['role']
            self.caveat = deets['caveat']
            self.specifics = (deets['specifics'] or '').strip()
        else:
            self.anime = None
            self.full_role = self.full_tag

        sortable_kinds: dict[str, tuple[int, str, str]] = {
            'op': (0, 'Opening theme', 'Opening themes'),
            'ed': (1, 'Ending theme', 'Ending themes'),
            'insert song': (2, 'Insert song', 'Insert songs'),
            'character song': (3, 'Character song', 'Character songs'),
        }

        if self.specifics:
            self.kind = self.full_role.removesuffix(self.specifics).strip()
        elif ' - ' in self.full_role:
            self.kind, self.specifics = self.full_role.split(' - ', 1)
        elif self.full_role.lower() in ('character song', 'insert song'):
            self.kind, self.specifics = (self.full_role, '')
        elif self.full_role.lower() in sortable_kinds.keys():
            self.kind = self.full_role
        else:
            self.kind, self.specifics = ('', self.full_role)

        self.sortkey_group, self.verbose, self.plural = sortable_kinds.get(
            self.kind.lower(), (99, 'Other', 'Others')
        )

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

    def anime_data(self) -> Optional[Anime]:
        return None if self.anime is None else get_anime(self.anime)

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


class Track(CleanOnSaveMixin, Serializable, models.Model):
    class Meta:
        constraints = [
            CheckConstraint(
                check=~Q(archived=True, hidden=True),
                name='track_cannot_be_both_hidden_and_archived',
            ),
            CheckConstraint(
                check=~Q(
                    hidden=False, archived=False, inudesu=False, revealed__isnull=True
                ),
                name='track_must_have_revealed_date_when_visible',
            ),
        ]

    objects = TrackQuerySet.as_manager()

    note_set: RelatedManager[Note]
    play_set: RelatedManager[Play]
    vote_set: RelatedManager[Vote]

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

    # derived from Myriad
    media_id = models.IntegerField(blank=True, null=True, unique=True)
    has_hook = models.BooleanField(
        help_text=(
            'Whether this track has a hook in Myriad. Null if not matched against a'
            ' Myriad export.'
        ),
        blank=True,
        null=True,
    )

    # nkdsu-specific
    revealed = models.DateTimeField(blank=True, null=True, db_index=True)
    archived = models.BooleanField(
        help_text=(
            'This will never be played again, but cannot be removed from the database'
            ' for historical reasons.'
        ),
        default=False,
    )
    hidden = models.BooleanField(
        help_text='This track has not been revealed, or is pending migration.'
    )
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
        return type(self) is type(other) and self.id == other.id

    def __hash__(self) -> int:
        return hash((type(self), self.id))

    def clean(self) -> None:
        # these checks can be deleted once we're on django 4.2, since they're enforced in a constraint
        # (be sure to preserve the nice error messages, though)
        if (
            (not self.inudesu)
            and (not self.hidden)
            and (not self.archived)
            and (not self.revealed)
        ):
            raise ValidationError(
                '{track} is visible but has no revealed date'.format(track=self)
            )
        if self.hidden and self.archived:
            raise ValidationError('Tracks cannot be both archived and hidden')

    @classmethod
    def all_anime_titles(cls) -> set[str]:
        return {
            rd.anime
            for t in cls.objects.public()
            for rd in t.role_details
            if rd.anime is not None
        }

    @classmethod
    def all_artists(cls) -> set[str]:
        return {a for t in cls.objects.public() for a in t.artist_names()}

    @classmethod
    def all_composers(cls) -> set[str]:
        return {c for t in cls.objects.public() for c in t.composer_names()}

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

        return {
            f'{role_detail.full_role}'
            f'\n | {role_detail.kind}\n | {role_detail.specifics}\n'
            for t in qs
            for role_detail in t.role_details
        }

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
    def plays_newest_first(self) -> models.QuerySet[Play]:
        return self.play_set.order_by('-date')

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

    @cached_property
    def title(self) -> str:
        return self.split_id3_title()[0]

    @cached_property
    def album(self) -> str:
        return self.id3_album

    @cached_property
    def role(self) -> Optional[str]:
        return self.split_id3_title()[1]

    @cached_property
    def roles(self) -> list[str]:
        return self.role.split('|') if self.role else []

    @cached_property
    def role_details(self) -> list[Role]:
        def quarter(anime_data: Optional[Anime]) -> str:
            return '_' if anime_data is None else anime_data.quarter

        return sorted(
            (Role(role) for role in self.roles), key=lambda r: quarter(r.anime_data())
        )

    def role_details_for_anime(self, anime: str) -> list[Role]:
        return [r for r in self.role_details if r.anime == anime]

    def has_anime(self, anime: str) -> bool:
        return anime in (r.anime for r in self.role_details)

    @cached_property
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
        Returns :data:`True` if this track can be requested.
        """

        return not self.ineligible()

    @memoize
    def ineligible(self) -> Optional[str]:
        """
        Return a string describing why a track is ineligible, or :data:`None`
        if it is not.
        """

        if self.inudesu:
            return 'inu desu'

        if self.hidden:
            return 'hidden'

        if self.archived:
            return 'archived'

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
    def notes(self) -> NoteQuerySet:
        return self.note_set.for_show_or_none(Show.current())

    @memoize
    def public_notes(self) -> NoteQuerySet:
        return self.notes().filter(public=True)

    def play_tweet_content(self) -> str:
        # here we add a zwsp after every . to prevent twitter from turning
        # things into links
        delinked_name = str(self).replace('.', '.\u200b')

        status = f'Now playing on {settings.HASHTAG}: {delinked_name}'

        if len(status) > settings.TWEET_LENGTH:
            # twitter counts ellipses as two characters for some reason, so we get rid of two:
            status = status[: settings.TWEET_LENGTH - 2].strip() + '…'

        return status

    def play_tweet_intent_url(self) -> str:
        return 'https://twitter.com/intent/tweet?text={text}'.format(
            text=quote(self.play_tweet_content())
        )

    def play(self) -> Play:
        """
        Mark this track as played.
        """

        return Play.objects.create(
            track=self,
            date=timezone.now(),
        )

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

    def archive(self) -> None:
        self.hidden = False
        self.archived = True
        self.save()

    archive.alters_data = True  # type: ignore

    def unarchive(self) -> None:
        self.archived = False
        self.save()

    unarchive.alters_data = True  # type: ignore

    def hide(self) -> None:
        self.archived = False
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

    def api_dict(self, verbose: bool = False) -> JsonDict:
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
            'added_week': (
                show_revealed.showtime.date().strftime('%Y-%m-%d')
                if show_revealed is not None
                else None
            ),
            'added': self.added.isoformat(),
            'url': self.get_public_url(),
            'background': self.background_art.url if self.background_art else None,
        }

        if verbose:
            the_track.update({'plays': [p.date for p in self.plays()]})

        return the_track


#: The kinds of vote that can be imported manually
MANUAL_VOTE_KINDS = (
    ('email', 'email'),
    ('discord', 'discord'),
    ('text', 'text'),
    ('tweet', 'tweet'),
    ('person', 'in person'),
    ('phone', 'on the phone'),
)


class VoteKind(Enum):
    #: A request made using the website's built-in requesting machinery.
    local = auto()

    #: A historical request, initially derived from a tweet we received via the Twitter API.
    twitter = auto()

    #: A request manually created by an admin to reflect, for example, an email.
    manual = auto()


class Vote(SetShowBasedOnDateMixin, CleanOnSaveMixin, models.Model):
    # universal
    tracks: models.ManyToManyField[Track, Any] = models.ManyToManyField(
        Track, db_index=True
    )
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

    def __hash__(self) -> int:
        return hash((type(self), self.id))

    def clean(self) -> None:
        match self.vote_kind:
            case VoteKind.manual:
                if self.tweet_id or self.twitter_user_id:
                    raise ValidationError('Twitter attributes present on manual vote')
                if self.user:
                    raise ValidationError('Local attributes present on manual vote')
                if not (self.name and self.kind):
                    raise ValidationError('Attributes missing from manual vote')
                return
            case VoteKind.twitter:
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

    @property
    def is_editable(self) -> bool:
        return self.show.showtime >= vote_edit_cutoff().showtime

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

        return u'{user} for {tracks}'.format(
            user=str(self.voter) if self.voter is not None else self.name,
            tracks=tracks,
        )

    @cached_property
    def voter(self) -> Optional[Voter]:
        match self.vote_kind:
            case VoteKind.manual:
                return None
            case VoteKind.twitter:
                return self.twitter_user
            case VoteKind.local:
                return self.user.profile if self.user else None

        assert_never(self.vote_kind)

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

    @cached_property
    def hat(self) -> Optional[UserBadge]:
        """
        Get the most important badge for a given vote, where the most important
        badge is the last one defined in :data:`BADGES` that we are currently
        within the time range of.
        """

        badge_order = [b.slug for b in BADGES]

        def get_badge_index(badge: UserBadge) -> int:
            return badge_order.index(badge.badge)

        if not self.voter:
            return None

        for badge in sorted(
            (
                b
                for b in UserBadge.for_voter(self.voter)
                if (
                    b.badge_info['start'] is None
                    or b.badge_info['start'] <= self.show.end
                )
                and (
                    b.badge_info['finish'] is None
                    or b.badge_info['finish'] >= self.show.end
                )
            ),
            key=get_badge_index,
            reverse=True,
        ):
            return badge

        return None

    @memoize
    @pk_cached(indefinitely)
    def success(self) -> Optional[float]:
        """
        Return how successful this :class:`Vote` is, as a :class:`float`
        between 0 and 1, or :data:`None` if we don't know yet.
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

    def api_dict(self, verbose: bool = False) -> JsonDict:
        tracks = self.tracks.all()
        the_vote: dict[str, Any] = {
            'comment': self.content() if self.content() != '' else None,
            'kind': self.vote_kind.name,
            'time': self.date,
            'track_ids': [t.id for t in tracks],
            'tracks': [t.api_dict() for t in tracks],
        }

        if self.vote_kind == VoteKind.twitter:
            assert self.twitter_user is not None
            the_vote.update({'tweet_id': self.tweet_id})
            the_vote.update(self.twitter_user.api_dict())

        if self.vote_kind == VoteKind.local:
            assert self.user is not None
            the_vote.update({'username': self.user.username})

        if self.vote_kind == VoteKind.manual:
            the_vote.update({'name': self.name, 'manual_vote_kind': self.kind})

        return the_vote

    def twitter_url(self) -> Optional[str]:
        if self.twitter_user is None or self.tweet_id is None:
            return None

        return 'https://twitter.com/%s/status/%s/' % (
            self.twitter_user.screen_name,
            self.tweet_id,
        )


class Play(SetShowBasedOnDateMixin, CleanOnSaveMixin, models.Model):
    """
    A record that a :class:`Track` was played on the show.
    """

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

    def api_dict(self, verbose: bool = False) -> JsonDict:
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
    A request for a database addition or modification.
    """

    #: keys of :attr:`blob` that no longer get set, but which may exist on historic :class:`Request`\ s
    METADATA_KEYS = ['trivia', 'trivia_question', 'contact']

    created = models.DateTimeField(auto_now_add=True)
    blob = models.TextField()
    submitted_by = models.ForeignKey(
        User,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name='submitted_requests',
        help_text='the person who submitted this request',
    )
    filled = models.DateTimeField(blank=True, null=True)
    filled_by = models.ForeignKey(
        User,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        help_text='the elf who fulfilled this request',
    )
    claimant = models.ForeignKey(
        User,
        blank=True,
        null=True,
        related_name='claims',
        on_delete=models.SET_NULL,
        help_text='the elf who is taking care of this request',
    )
    track = models.ForeignKey(
        Track,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        help_text=(
            'the track that this request is about, if this is a request for a'
            ' correction'
        ),
    )

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

    @cached_property
    def active_shelving(self) -> Optional[ElfShelving]:
        try:
            return self.shelvings.get(disabled_at__isnull=True)
        except ElfShelving.DoesNotExist:
            return None

    @property
    def is_shelved(self) -> bool:
        """
        >>> from django.utils import timezone
        >>> user = User.objects.create()
        >>> request = Request(blob='{}')
        >>> request.save()
        >>> request.is_shelved
        False
        >>> shelving = ElfShelving.objects.create(request=request, created_by=user)
        >>> del request.active_shelving  # to make @cached_property forget the cached response
        >>> request.is_shelved
        True
        >>> shelving.disabled_at = timezone.now()
        >>> shelving.save()
        >>> del request.active_shelving
        >>> request.is_shelved
        False
        """
        return self.active_shelving is not None

    class Meta:
        ordering = ['-created']


class ElfShelving(CleanOnSaveMixin, models.Model):
    """
    An expression by a :ref:`elf <elfs>` that a :class:`Request` cannot be
    :attr:`~.Request.filled` at the moment.
    """

    request = models.ForeignKey(
        Request, on_delete=models.CASCADE, related_name='shelvings'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name='created_shelvings'
    )
    reason_created = models.TextField(blank=True)

    disabled_at = models.DateTimeField(blank=True, null=True)
    disabled_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='disabled_shelvings',
        blank=True,
        null=True,
    )
    reason_disabled = models.TextField(blank=True)


class Note(CleanOnSaveMixin, models.Model):
    """
    A note about whatever for a particular track.
    """

    objects = NoteQuerySet.as_manager()

    track = models.ForeignKey(Track, on_delete=models.CASCADE)
    show = models.ForeignKey(Show, blank=True, null=True, on_delete=models.CASCADE)
    public = models.BooleanField(default=False)
    content = models.TextField()

    def __str__(self) -> str:
        return self.content


class ProRouletteCommitment(CleanOnSaveMixin, models.Model):
    """
    A commitment from a given user to only use :class:`.Roulette` in 'pro' mode
    until the current show ends. Retains the track they committed to and when
    the commitment was made.
    """

    show = models.ForeignKey(Show, on_delete=models.PROTECT)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    track = models.ForeignKey(Track, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                *('show', 'user'),
                name='pro_roulette_commitment_unique',
                violation_error_message='a user can only have one pro roulette commitment per show',
            )
        ]


class BadgeInfoForUser(TypedDict):
    slug: str
    description: str
    summary: str
    icon: str
    url: str
    start: Optional[datetime.datetime]
    finish: Optional[datetime.datetime]


@dataclass
class Badge:
    slug: str
    description_fmt: str
    summary: str
    icon: str
    url: str
    start: Optional[datetime.datetime]
    finish: Optional[datetime.datetime]

    def info(self, user: Voter) -> BadgeInfoForUser:
        return {
            'slug': self.slug,
            'description': self.description_fmt.format(name=user.name),
            'summary': self.summary,
            'icon': self.icon,
            'url': self.url,
            'start': Show.at(self.start).showtime if self.start is not None else None,
            'finish': Show.at(self.finish).end if self.finish is not None else None,
        }


#: A list of accolades we can give to users for showing off on user pages and,
#: during a specified time range, against every :class:`Vote` they make.
BADGES: list[Badge] = [
    Badge(
        'tblc',
        u'{name} bought Take Back Love City for the RSPCA.',
        'put up with bad music for animals',
        'headphones',
        'https://desus.bandcamp.com/album/take-back-love-city',
        None,
        datetime.datetime(1990, 1, 1, tzinfo=get_default_timezone()),
    ),
    Badge(
        'charity-2016',
        u'{name} donated to the Very Scary Scenario charity streams for '
        u'Special Effect in 2016.',
        'likes fun, hates exclusion',
        'heart',
        'https://www.justgiving.com/fundraising/very-scary-scenario',
        datetime.datetime(2016, 10, 15, tzinfo=get_default_timezone()),
        datetime.datetime(2016, 11, 15, tzinfo=get_default_timezone()),
    ),
    Badge(
        'charity-2017',
        u'{name} donated to the Very Scary Scenario charity streams and '
        u'Neko Desu All-Nighter for Cancer Research UK in 2017.',
        'likes depriving people of sleep, hates cancer',
        'heart',
        'https://www.justgiving.com/fundraising/very-charity-scenario-2017',
        datetime.datetime(2017, 10, 1, tzinfo=get_default_timezone()),
        datetime.datetime(2017, 11, 27, tzinfo=get_default_timezone()),
    ),
    Badge(
        'charity-2018',
        u'{name} donated to the Very Scary Scenario charity streams for '
        u'Cancer Research UK in 2018.',
        'likes depriving people of sleep, hates cancer',
        'medkit',
        'https://www.justgiving.com/fundraising/very-charity-scenario-2018',
        datetime.datetime(2018, 10, 1, tzinfo=get_default_timezone()),
        datetime.datetime(2018, 11, 27, tzinfo=get_default_timezone()),
    ),
    Badge(
        'charity-2019',
        u'{name} donated to the Very Scary Scenario charity streams for '
        u'Samaritans in 2019.',
        'likes depriving people of sleep, fan of good mental health',
        'life-ring',
        'https://www.justgiving.com/fundraising/very-charity-scenario-2019',
        datetime.datetime(2019, 10, 1, tzinfo=get_default_timezone()),
        datetime.datetime(2019, 11, 27, tzinfo=get_default_timezone()),
    ),
    Badge(
        'charity-2020',
        u'{name} donated to the Very Scary Scenario charity streams for '
        u'Cancer Research UK in 2020.',
        'donated to the 2020 Very Scary Scenario charity streams',
        'heartbeat',
        'https://www.justgiving.com/fundraising/very-charity-scenario-2020',
        datetime.datetime(2020, 10, 1, tzinfo=get_default_timezone()),
        datetime.datetime(2020, 11, 27, tzinfo=get_default_timezone()),
    ),
    Badge(
        'charity-2021',
        u'{name} donated to the Very Scary Scenario charity streams for Mind in 2021.',
        'donated to the 2021 Very Scary Scenario charity streams',
        'brain',
        'https://www.justgiving.com/fundraising/very-charity-scenario-2021',
        datetime.datetime(2021, 10, 9, tzinfo=get_default_timezone()),
        datetime.datetime(2021, 11, 27, tzinfo=get_default_timezone()),
    ),
    Badge(
        'charity-2022',
        u'{name} donated to the Very Scary Scenario charity streams for akt in 2022.',
        'donated to the 2022 Very Scary Scenario charity streams',
        'home',
        'https://www.justgiving.com/fundraising/very-charity-scenario-2022',
        datetime.datetime(2022, 10, 9, tzinfo=get_default_timezone()),
        datetime.datetime(2022, 11, 27, tzinfo=get_default_timezone()),
    ),
    Badge(
        'charity-2023',
        '{name} donated to the Very Scary Scenario charity streams and '
        'Neko Desu All-Nighter for the National Autistic Society in 2023.',
        'donated to the 2023 Very Scary Scenario charity streams',
        'infinity',
        'https://www.justgiving.com/page/very-charity-scenario-2023',
        datetime.datetime(2023, 9, 9, tzinfo=get_default_timezone()),
        datetime.datetime(2023, 12, 2, tzinfo=get_default_timezone()),
    ),
]


class UserBadge(CleanOnSaveMixin, models.Model):
    badge = models.CharField(
        choices=[(b.slug, b.description_fmt) for b in BADGES],
        max_length=max((len(b.slug) for b in BADGES)),
    )
    twitter_user = models.ForeignKey(
        TwitterUser, on_delete=models.CASCADE, blank=True, null=True
    )
    profile = models.ForeignKey(
        Profile, on_delete=models.CASCADE, blank=True, null=True
    )

    @classmethod
    def for_voter(cls, voter: Voter) -> models.QuerySet[UserBadge]:
        twu: Optional[TwitterUser]
        prf: Optional[Profile]
        twu, prf = voter._twitter_user_and_profile()
        return cls.objects.filter(
            Q(profile=prf, profile__isnull=False)
            | Q(twitter_user=twu, twitter_user__isnull=False)
        ).order_by('pk')

    def clean(self) -> None:
        if self.twitter_user is not None:
            try:
                profile = self.twitter_user.profile
            except Profile.DoesNotExist:
                pass
            else:
                raise ValidationError(
                    {
                        'twitter_user': (
                            'This Twitter user has a profile you should use instead. '
                            f'"{self.twitter_user}" has a profile called "{profile}"'
                        )
                    }
                )

    @cached_property
    def badge_info(self) -> BadgeInfoForUser:
        (badge,) = (b for b in BADGES if b.slug == self.badge)

        u = self.profile or self.twitter_user
        if u is None:
            raise RuntimeError(f'badge {self.pk} has no profile and no twitter user')

        return badge.info(u)

    class Meta:
        constraints = [
            CheckConstraint(
                check=Q(profile__isnull=True, twitter_user__isnull=False)
                | Q(profile__isnull=False, twitter_user__isnull=True),
                name='badge_must_have_user',
                violation_error_message=(
                    'Badges must be associated with either a profile or twitter user'
                ),
            ),
            # until we handle this when creating profile objects, this check should not be enforced in the database:
            # CheckConstraint(
            #     check=Q(twitter_user__isnull=False, twitter_user__profile__isnull=True),
            #     name='badge_must_use_profile_if_available',
            # ),
        ]
