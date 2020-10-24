# -*- coding: utf-8 -*-

from io import BytesIO
import datetime
import json
import re
from string import ascii_letters
from urllib.parse import urlparse

from classtools import reify
from dateutil import parser as date_parser
from Levenshtein import ratio
from markdown import markdown
from PIL import Image, ImageFilter
import requests

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile
from django.urls import resolve, Resolver404
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.template.defaultfilters import slugify
from django.conf import settings
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.templatetags.static import static
from django.utils.timezone import get_default_timezone

from .managers import TrackManager, NoteManager
from .parsers import parse_artist
from .utils import (
    length_str, split_id3_title, vote_tweet_intent_url, reading_tw_api,
    posting_tw_api, memoize, pk_cached, indefinitely, lastfm, musicbrainzngs
)
from ..vote import mixcloud


User = get_user_model()


class CleanOnSaveMixin(object):
    def save(self, force_save=False):
        if not force_save:
            self.full_clean()

        return super(CleanOnSaveMixin, self).save()


class SetShowBasedOnDateMixin(object):
    def save(self, *args, **kwargs):
        self.show = Show.at(self.date)
        return super(SetShowBasedOnDateMixin, self).save(*args, **kwargs)


class Show(CleanOnSaveMixin, models.Model):
    """
    A broadcast of the show and, by extention, the week leading up to it.
    """

    showtime = models.DateTimeField(db_index=True)
    end = models.DateTimeField(db_index=True)
    message = models.TextField(blank=True)
    voting_allowed = models.BooleanField(default=True)

    def __str__(self):
        return self.showtime.date().isoformat()

    def __repr__(self):
        return str(self)

    def clean(self):
        if self.end < self.showtime:
            raise ValidationError(
                'Show ends before it begins; {end} < {start}'.format(
                    end=self.end, start=self.showtime))
        overlap = Show.objects.exclude(pk=self.pk).filter(
            showtime__lt=self.end,
            end__gt=self.showtime)
        if overlap.exists():
            raise ValidationError(
                '{self} overlaps existing shows: {overlap}'.format(
                    self=self, overlap=overlap))

    @classmethod
    def current(cls):
        """
        Get (or create, if necessary) the show that will next end.
        """

        return cls.at(timezone.now())

    @classmethod
    def _at(cls, time, create=True):
        """
        Get (or create, if necessary) the show for `time`. Use .at() instead.
        """

        shows_after_time = cls.objects.filter(end__gt=time)

        try:
            return shows_after_time.order_by('showtime')[0]
        except IndexError:
            pass

        if create:
            # We have to switch to naive and back to make relativedelta
            # look for the local showtime. If we did not, showtime would be
            # calculated against UTC.
            naive_time = timezone.make_naive(time,
                                             timezone.get_current_timezone())
            naive_end = naive_time + settings.SHOW_END

            # Work around an unfortunate shortcoming of dateutil where
            # specifying a time on a weekday won't increment the weekday even
            # if our initial time is after that time.
            while naive_end < naive_time:
                naive_time += datetime.timedelta(hours=1)
                naive_end = naive_time + settings.SHOW_END

            naive_showtime = naive_end - settings.SHOWTIME

            our_end = timezone.make_aware(naive_end,
                                          timezone.get_current_timezone())
            our_showtime = timezone.make_aware(naive_showtime,
                                               timezone.get_current_timezone())
            show = cls()
            show.end = our_end
            show.showtime = our_showtime
            show.save()
            return show

    @classmethod
    def at(cls, time):
        """
        Get the show for the date specified, creating every intervening show
        in the process if necessary.
        """

        all_shows = cls.objects.all()
        if cache.get('all_shows:exists') or all_shows.exists():
            cache.set('all_shows:exists', True, None)
            last_show = all_shows.order_by('-end')[0]
        else:
            return cls._at(time)  # this is the first show!

        if time <= last_show.end:
            return cls._at(time)

        show = last_show

        while show.end < time:
            show = show.next(create=True)

        return show

    @memoize
    def broadcasting(self, time=None):
        """
        Return True if the time specified is during this week's show.
        """

        if time is None:
            time = timezone.now()

        return (time >= self.showtime) and (time < self.end)

    @memoize
    @pk_cached(indefinitely)
    def next(self, create=False):
        """
        Return the next Show.
        """

        return Show._at(self.end + datetime.timedelta(microseconds=1), create)

    @memoize
    @pk_cached(indefinitely)
    def prev(self):
        """
        Return the previous Show.
        """

        qs = Show.objects.filter(end__lt=self.end)

        try:
            return qs.order_by('-showtime')[0]
        except IndexError:
            return None

    def has_ended(self):
        return timezone.now() > self.end

    def _date_kwargs(self, attr='date'):
        """
        The kwargs you would hand to a queryset to find objects applicable to
        this show. Should not be used unless you're doing something that
        can't use a .show ForeignKey.
        """

        kw = {'%s__lte' % attr: self.end}

        if self.prev() is not None:
            kw['%s__gt' % attr] = self.prev().end

        return kw

    @memoize
    def votes(self):
        return self.vote_set.all()

    @memoize
    def plays(self):
        return self.play_set.order_by('date')

    @memoize
    def playlist(self):
        return [p.track for p in self.plays().select_related('track')]

    @memoize
    def shortlisted(self):
        return list(filter(lambda t: t not in self.playlist(),
                           (p.track for p in self.shortlist_set.all())))

    @memoize
    def discarded(self):
        return list(filter(lambda t: t not in self.playlist(),
                           (p.track for p in self.discard_set.all())))

    @memoize
    @pk_cached(20)
    def tracks_sorted_by_votes(self):
        """
        Return a list of tracks that have been voted for this week, in order of
        when they were last voted for, starting from the most recent.
        """

        track_set = set()
        tracks = []

        votes = Vote.objects.filter(show=self).filter(
            Q(twitter_user__is_abuser=False) |
            Q(twitter_user__isnull=True)
        ).prefetch_related('tracks').order_by('-date')

        for track in (
            track for vote in votes for track in vote.tracks.all()
        ):
            if track.pk in track_set:
                continue

            track_set.add(track.pk)
            tracks.append(track)

        return tracks

    @memoize
    @pk_cached(60)
    def revealed(self, show_hidden=False):
        """
        Return a all public (unhidden, non-inudesu) tracks revealed in the
        library this week.
        """

        return Track.objects.filter(hidden=False, inudesu=False,
                                    **self._date_kwargs('revealed'))

    @memoize
    @pk_cached(60)
    def cloudcasts(self):
        return mixcloud.cloudcasts_for(self.showtime)

    def get_absolute_url(self):
        if self == Show.current():
            return reverse('vote:index')

        return reverse('vote:show', kwargs={
            'date': self.showtime.date().strftime('%Y-%m-%d')
        })

    def get_listen_url(self):
        return reverse('vote:listen-to-show', kwargs={
            'date': self.showtime.date().strftime('%Y-%m-%d')
        })

    def get_revealed_url(self):
        return reverse('vote:added', kwargs={
            'date': self.showtime.date().strftime('%Y-%m-%d')
        })

    @reify
    def start(self):
        prev = self.prev()

        if prev is None:
            return None
        else:
            return prev.end

    def api_dict(self, verbose=False):
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
    # Twitter stuff
    screen_name = models.CharField(max_length=100)
    user_id = models.BigIntegerField(unique=True)
    name = models.CharField(max_length=100)

    # nkdsu stuff
    is_patron = models.BooleanField(default=False)
    is_abuser = models.BooleanField(default=False)
    updated = models.DateTimeField()

    def __str__(self):
        return str(self.screen_name)

    def __repr__(self):
        return self.screen_name

    def twitter_url(self):
        return 'https://twitter.com/%s' % self.screen_name

    def get_absolute_url(self):
        return reverse('vote:user', kwargs={'screen_name': self.screen_name})

    def get_toggle_abuser_url(self):
        return reverse('vote:admin:toggle_abuser',
                       kwargs={'user_id': self.user_id})

    def get_avatar_url(self):
        return reverse('vote:avatar', kwargs={'user_id': self.user_id})

    @memoize
    def get_avatar(self, size=None, from_cache=True):
        ck = f'twav:{size}:{self.pk}'

        if from_cache:
            hit = cache.get(ck)
            if hit:
                return hit

        url = self.get_twitter_user().profile_image_url_https
        if size is not None:
            if size != 'original':
                size = '_{}'.format(size)
            else:
                size = ''
            url = re.sub(r'_normal(?=\.[^.]+$)', size, url)
        resp = requests.get(url)
        rv = (resp.headers['content-type'], resp.content)

        # update_twitter_avatars will call this every day with
        # from_cache=False, and might sometimes fail, so:
        cache.set(ck, rv, (60 * 60 * 24 * 2.1))

        return rv

    @memoize
    def votes(self):
        return self.vote_set.order_by('-date').prefetch_related('tracks')

    @memoize
    def votes_with_liberal_preselection(self):
        return self.votes().prefetch_related(
            'show',
            'show__play_set',
            'show__play_set__track',  # doesn't actually appear to work :<
        )

    @memoize
    def votes_for(self, show):
        return self.votes().filter(show=show)

    @memoize
    def tracks_voted_for_for(self, show):
        tracks = []
        track_pk_set = set()

        for vote in self.votes_for(show):
            for track in vote.tracks.all():
                if track.pk not in track_pk_set:
                    track_pk_set.add(track.pk)
                    tracks.append(track)

        return tracks

    def _batting_average(self, cutoff=None, minimum_weight=1):
        def ba(pk, current_show_pk, cutoff):
            score = 0
            weight = 0

            for vote in self.vote_set.filter(date__gt=cutoff).prefetch_related(
                    'tracks'):
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
            return

        return score

    @memoize
    def batting_average(self, minimum_weight=1):
        """
        Return a user's batting average for the past six months.
        """

        return self._batting_average(
            cutoff=Show.at(timezone.now() - datetime.timedelta(days=31*6)).end,
            minimum_weight=minimum_weight
        )

    def _streak(self, ls=[]):
        show = Show.current().prev()
        streak = 0

        while True:
            if not show.voting_allowed:
                show = show.prev()
            elif show.votes().filter(twitter_user=self).exists():
                streak += 1
                show = show.prev()
            else:
                break

        return streak

    @memoize
    def streak(self):
        def streak(pk, current_show):
            return self._streak()

        return streak(self.pk, Show.current())

    def all_time_batting_average(self, minimum_weight=1):
        return self._batting_average(minimum_weight=minimum_weight)

    @memoize
    @pk_cached(60*60*1)
    def get_twitter_user(self):
        return reading_tw_api.get_user(user_id=self.user_id)

    def update_from_api(self):
        """
        Update this user's database object based on the Twitter API.
        """

        api_user = self.get_twitter_user()

        self.name = api_user.name
        self.screen_name = api_user.screen_name
        self.updated = timezone.now()

        self.save()

    def api_dict(self, verbose=False):
        return {
            'user_name': self.name,
            'user_screen_name': self.screen_name,
            'user_image': self.get_avatar_url(),
            'user_id': self.user_id,
        }

    @memoize
    def is_new(self):
        return not self.vote_set.exclude(show=Show.current()).exists()

    @memoize
    def is_placated(self):
        return self.vote_set.filter(
            tracks__play__show=Show.current(),
            show=Show.current(),
        ).exists()

    @memoize
    def is_shortlisted(self):
        return self.vote_set.filter(
            tracks__shortlist__show=Show.current(),
            show=Show.current(),
        ).exists()


def art_path(i, f):
    return 'art/bg/%s.%s' % (i.pk, f.split('.')[-1])


def _name_is_related(a, b):
    return (
        (
            # exclude cases where this is a subword match (to avoid matching
            # 'rec' to 'record', for instance):

            # none of these checks matter if b is the longer string or they're
            # the same length
            (len(a) <= len(b)) or

            a[len(b)] not in ascii_letters or

            b[-1] not in ascii_letters

        ) and

        # run our actual comparison
        ratio(a[:len(b)].lower(), b.lower()) > 0.8
    )


class Role:
    def __init__(self, full_tag):
        self.full_tag = full_tag

        result = re.match(
            r'^(?P<anime>.*?) ?\b(?P<role>'

            r'(rebroadcast )?\b('

            r'((ED|OP)\d*\b.*)|'
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
        else:
            self.anime = None
            self.full_role = self.full_tag

        if self.full_role[:2] in ('OP', 'ED'):
            self.kind, self.specifics = (
                self.full_role[:2], self.full_role[2:].strip(),
            )
        elif self.full_role[:11].lower() == 'insert song':
            self.kind, self.specifics = (
                self.full_role[:11], self.full_role[11:].strip()
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

    def __str__(self):
        return self.full_tag

    def __lt__(self, other):
        return self.sortkey() < other.sortkey()

    def __gt__(self, other):
        return self.sortkey() > other.sortkey()

    def numbers_in_role(self):
        # basically intended to ensure 'op10' is sorted after 'op9', but also
        # will work perfectly for cases where there's stuff like 'season 3
        # ep10-13'
        return tuple((int(n) for n in re.findall(r'\d+', self.full_role)))

    def sortkey(self):
        return (
            self.sortkey_group,
            self.kind,
            self.numbers_in_role(),
            self.full_tag,
        )

    def anime_is_related(self, anime):
        return (
            len(self.anime) > 1 and
            len(anime) > 1
        ) and (
            _name_is_related(anime, self.anime) or
            _name_is_related(self.anime, anime)
        )

    def related_anime(self):
        return [a for a in Track.all_anime_titles()
                if a != self.anime and self.anime_is_related(a)]


class Track(CleanOnSaveMixin, models.Model):
    objects = TrackManager()

    # derived from iTunes
    id = models.CharField(max_length=16, primary_key=True)
    id3_title = models.CharField(max_length=500)
    id3_artist = models.CharField(max_length=500)
    id3_album = models.CharField(max_length=500, blank=True)
    msec = models.IntegerField(blank=True, null=True)
    added = models.DateTimeField()
    composer = models.CharField(max_length=500, blank=True)
    label = models.CharField(max_length=500, blank=True)

    # nkdsu-specific
    revealed = models.DateTimeField(blank=True, null=True, db_index=True)
    hidden = models.BooleanField()
    inudesu = models.BooleanField()
    background_art = models.ImageField(blank=True, upload_to=art_path)
    metadata_locked = models.BooleanField(default=False)

    def __str__(self):
        """
        The string that, for instance, would be tweeted
        """

        if self.role:
            return u'‘%s’ (%s) - %s' % (self.title, self.role, self.artist)
        else:
            return u'‘%s’ - %s' % (self.title, self.artist)

    def __eq__(self, other):
        return type(self) == type(other) and self.id == other.id

    def __hash__(self):
        return hash(self.id)

    def clean(self):
        if (not self.inudesu) and (not self.hidden) and (not self.revealed):
            raise ValidationError('{track} is not hidden but has no revealed '
                                  'date'.format(track=self))

    @classmethod
    def all_anime_titles(cls):
        return set(
            (rd.anime for t in cls.objects.public() for rd in t.role_details)
        )

    @classmethod
    def all_artists(cls):
        return set(
            a
            for t in cls.objects.all()
            for a in t.artist_names()
        )

    @classmethod
    def suggest_artists(cls, string):
        artist_names = set()
        for track in Track.objects.public().filter(
            id3_artist__icontains=string
        ):
            for artist_name in track.artist_names():
                artist_names.add(artist_name)

        return artist_names

    @classmethod
    def all_roles(cls, qs=None):
        if qs is None:
            qs = cls.objects.all()

        return set((
            f'{role_detail.full_role}'
            f'\n | {role_detail.kind}\n | {role_detail.specifics}\n'
            for t in qs for role_detail in t.role_details
        ))

    @classmethod
    def all_non_inudesu_roles(cls):
        return cls.all_roles(cls.objects.filter(inudesu=False))

    @memoize
    def is_new(self):
        return Show.current() == self.show_revealed()

    @memoize
    def show_revealed(self):
        """
        Return the show that this track was revealed for.
        """

        if self.revealed:
            return Show.at(self.revealed)

    def length_str(self):
        return length_str(self.msec)

    @memoize
    def last_play(self):
        try:
            return self.play_set.order_by('-date')[0]
        except IndexError:
            return False

    @memoize
    def plays(self):
        return self.play_set.order_by('date')

    @memoize
    def weeks_since_play(self):
        """
        Get the number of weeks since this track's last Play.
        """

        if not self.last_play():
            return

        show = Show.current()

        return (show.end - self.last_play().date).days // 7

    @reify
    def title(self):
        return self.split_id3_title()[0]

    @reify
    def album(self):
        return self.id3_album

    @reify
    def role(self):
        return self.split_id3_title()[1]

    @reify
    def roles(self):
        return self.role.split('|') if self.role else []

    @reify
    def role_details(self):
        return [Role(role) for role in self.roles]

    def role_detail_for_anime(self, anime):
        self._recently_relevant_anime = anime
        details, = [r for r in self.role_details if r.anime == anime]
        return details

    def role_detail_for_recently_relevant_anime(self):
        return self.role_detail_for_anime(self._recently_relevant_anime)

    def has_anime(self, anime):
        return anime in (r.anime for r in self.role_details)

    @reify
    def artist(self):
        return self.id3_artist

    def artist_names(self, fail_silently=True):
        return (
            name for is_artist_name, name in
            parse_artist(self.artist, fail_silently=fail_silently)
            if is_artist_name
        )

    @memoize
    @pk_cached(90)
    def artists(self):
        return [
            {
                'url': (
                    reverse('vote:artist', kwargs={'artist': bit_of_string})
                    if is_artist_name else None
                ),
                'name': bit_of_string,
                'worth_linking_to': bool(
                    is_artist_name and
                    Track.objects.by_artist(bit_of_string)
                )
            }
            for is_artist_name, bit_of_string in parse_artist(self.artist)
        ]

    def split_id3_title(self):
        return split_id3_title(self.id3_title)

    def eligible(self):
        """
        Returns True if this track can be requested.
        """

        return not self.ineligible()

    @memoize
    def ineligible(self):
        """
        Return a string describing why a track is ineligible, or False if it
        is not
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

        return False

    @memoize
    @pk_cached(10)
    def votes_for(self, show):
        """
        Return votes for this track for a given show.
        """

        return self.vote_set.filter(show=show).order_by('date')

    @memoize
    def notes(self):
        return self.note_set.for_show_or_none(Show.current())

    @memoize
    def public_notes(self):
        return self.notes().filter(public=True)

    def play(self, tweet=True):
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

    play.alters_data = True

    def shortlist(self):
        shortlist = Shortlist(
            track=self,
            show=Show.current(),
        )
        shortlist.take_first_available_index()

        try:
            shortlist.save()
        except ValidationError:
            pass

    shortlist.alters_data = True

    def discard(self):
        try:
            Discard(
                track=self,
                show=Show.current(),
            ).save()
        except ValidationError:
            pass

    discard.alters_data = True

    def reset_shortlist_discard(self):
        qs_kwargs = {'track': self, 'show': Show.current()}
        Discard.objects.filter(**qs_kwargs).delete()
        Shortlist.objects.filter(**qs_kwargs).delete()

    reset_shortlist_discard.alters_data = True

    def hide(self):
        self.hidden = True
        self.save()

    hide.alters_data = True

    def unhide(self):
        self.hidden = False

        if not self.revealed:
            self.revealed = timezone.now()

        self.save()

    unhide.alters_data = True

    def lock_metadata(self):
        self.metadata_locked = True
        self.save()

    lock_metadata.alters_data = True

    def unlock_metadata(self):
        self.metadata_locked = False
        self.save()

    unlock_metadata.alters_data = True

    def slug(self):
        return slugify(self.title)

    def get_absolute_url(self):
        return reverse('vote:track', kwargs={'slug': self.slug(),
                                             'pk': self.pk})

    def get_public_url(self):
        return settings.SITE_URL + self.get_absolute_url()

    def get_report_url(self):
        return reverse('vote:report', kwargs={'pk': self.pk})

    def get_vote_url(self):
        """
        Return the Twitter intent url for voting for this track alone.
        """

        return vote_tweet_intent_url([self])

    def get_lastfm_track(self):
        return lastfm(
            method='track.getInfo',
            track=self.title,
            artist=self.artist,
        ).get('track')

    @memoize
    @pk_cached(3600)
    def musicbrainz_release(self):
        releases = musicbrainzngs.search_releases(
            tracks=self.title,
            release=self.album,
            artist=self.artist,
        ).get('release-list')

        official_releases = [r for r in releases
                             if r.get('status') == 'Official']

        if official_releases:
            return official_releases[0]
        elif releases:
            return releases[0]

    def _get_lastfm_album_from_album_tag(self):
        return lastfm(
            method='album.getInfo',
            artist=self.artist,
            album=self.album,
        ).get('album')

    def _get_lastfm_album_from_musicbrainz_release(self):
        release = self.musicbrainz_release()

        if release is not None:
            return lastfm(
                method='album.getInfo',
                artist=release['artist-credit-phrase'],
                album=release['title'],
            ).get('album')

    def _get_lastfm_album_from_track_tag(self):
        track = self.get_lastfm_track()

        if track is not None:
            return track.get('album')

    def get_lastfm_album(self):
        album = self._get_lastfm_album_from_album_tag()

        if album is not None:
            return album
        else:
            return self._get_lastfm_album_from_track_tag()

    def get_lastfm_artist(self):
        return lastfm(method='artist.getInfo', artist=self.artist
                      ).get('artist')

    def get_biggest_lastfm_image_url(self):
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

    def update_background_art(self):
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

        self.background_art.save(image_url.split('/')[-1] + suffix,
                                 File(temp_file))

    def api_dict(self, verbose=False):
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
            'artists_parsed': self.artists(),
            'eligible': self.eligible(),
            'ineligibility_reason': self.ineligible() or None,
            'length': self.msec,
            'inu desu': self.inudesu,
            'url': self.get_public_url(),
            'background': (
                self.background_art.url
                if self.background_art
                else None
            ),
        }

        if verbose:
            the_track.update({
                'plays': [p.date for p in self.plays()],
            })

        return the_track


MANUAL_VOTE_KINDS = (
    ('email', 'email'),
    ('text', 'text'),
    ('tweet', 'tweet'),
    ('person', 'in person'),
    ('phone', 'on the phone'),
)


class Vote(SetShowBasedOnDateMixin, CleanOnSaveMixin, models.Model):
    # universal
    tracks = models.ManyToManyField(Track, db_index=True)
    date = models.DateTimeField(db_index=True)
    show = models.ForeignKey(Show, related_name='vote_set',
                             on_delete=models.CASCADE)
    text = models.TextField(blank=True)

    # twitter only
    twitter_user = models.ForeignKey(TwitterUser, blank=True, null=True,
                                     db_index=True, on_delete=models.SET_NULL)
    tweet_id = models.BigIntegerField(blank=True, null=True)

    # manual only
    name = models.CharField(max_length=40, blank=True)
    kind = models.CharField(max_length=10, choices=MANUAL_VOTE_KINDS,
                            blank=True)

    @classmethod
    def handle_tweet(cls, tweet):
        """
        Take a tweet json object and create, save and return the vote it should
        come to represent (or None if it's not a valid vote).
        """

        text = tweet.get('full_text', None) or tweet.get('text', None)

        if text is None:
            if 'delete' in tweet:
                Vote.objects.filter(
                    tweet_id=tweet['delete']['status']['id']
                ).delete()
            return

        if cls.objects.filter(tweet_id=tweet['id']).exists():
            return  # we already have this tweet

        created_at = date_parser.parse(tweet['created_at'])

        def mention_is_first_and_for_us(mention):
            return (
                mention['indices'][0] == 0 and
                mention['screen_name'] == settings.READING_USERNAME
            )

        if not any([mention_is_first_and_for_us(m)
                    for m in tweet['entities']['user_mentions']]):
            return

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
        for url in (
            tweet.get('extended_entities') or tweet.get('entities', {})
        ).get('urls', ()):
            parsed = urlparse(url['expanded_url'])

            try:
                match = resolve(parsed.path)
            except Resolver404:
                continue

            if (
                match.namespace == 'vote' and
                match.url_name == 'track'
            ):
                track_qs = Track.objects.public().filter(pk=match.kwargs['pk'])

                try:
                    track = track_qs.get()
                except Track.DoesNotExist:
                    continue

                if (track.pk not in (
                    t.pk for t in twitter_user.tracks_voted_for_for(show)
                ) and track.eligible()):
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

    def clean(self):
        if self.is_manual:
            if self.tweet_id or self.twitter_user_id:
                raise ValidationError(
                    'Twitter attributes present on manual vote')
            if not (self.name and self.kind):
                raise ValidationError(
                    'Attributes missing from manual vote')
        else:
            if self.name or self.kind:
                raise ValidationError(
                    'Manual attributes present on Twitter vote')
            if not (self.tweet_id and self.twitter_user_id):
                raise ValidationError(
                    'Twitter attributes missing from Twitter vote')

    def either_name(self):
        return self.name or '@{0}'.format(self.twitter_user.screen_name)

    @reify
    def is_manual(self):
        return not bool(self.tweet_id)

    def get_image_url(self):
        if self.twitter_user:
            return self.twitter_user.get_avatar_url()
        else:
            return static('i/vote-kinds/{0}.png'.format(self.kind))

    def __str__(self):
        tracks = u', '.join([t.title for t in self.tracks.all()])

        return u'{user} at {date} for {tracks}'.format(
            user=self.name or self.twitter_user,
            date=self.date,
            tracks=tracks,
        )

    @memoize
    def content(self):
        """
        Return the non-mention, non-url content of the text.
        """

        content = self.text

        if not self.is_manual:
            while (
                content.lower()
                .startswith('@{}'.format(settings.READING_USERNAME).lower())
            ):
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
    def birthday(self):
        content = self.content()
        return (
            content and
            re.search(r'\b(birthday|b-?day)', content, flags=re.IGNORECASE)
        )

    @reify
    def hat(self):
        """
        Get the most important badge for a given vote, where the most important
        badge is the last one defined in `BADGES`.
        """

        badge_order = [b[0] for b in BADGES]

        if not self.twitter_user:
            return

        for badge in sorted(
            (
                b for b in self.twitter_user.userbadge_set.all()
                if (
                    b.badge_info['start'] is None or
                    b.badge_info['start'] <= self.show.end
                ) and (
                    b.badge_info['finish'] is None or
                    b.badge_info['finish'] >= self.show.end
                )
            ),
            key=lambda b: badge_order.index(b.badge),
            reverse=True,
        ):
            return badge

    @memoize
    @pk_cached(indefinitely)
    def success(self):
        """
        Return how successful this vote is, as a float between 0 and 1, or None
        if we don't know yet.
        """

        if not self.show.has_ended():
            return

        successes = 0
        for track in self.tracks.all():
            if track in self.show.playlist():
                successes += 1

        return successes / self.weight()

    @memoize
    @pk_cached(indefinitely)
    def weight(self):
        """
        Return how much we should take this vote into account when calculating
        a user's batting average.
        """

        return float(self.tracks.all().count())

    def api_dict(self, verbose=False):
        tracks = self.tracks.all()
        the_vote = {
            'comment': self.content() if self.content() != '' else None,
            'time': self.date,
            'track_ids': [t.id for t in tracks],
            'tracks': [t.api_dict() for t in tracks],
        }

        if not self.is_manual:
            the_vote.update({
                'tweet_id': self.tweet_id,
            })
            the_vote.update(self.twitter_user.api_dict())

        return the_vote

    def twitter_url(self):
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

    def clean(self):
        for play in self.show.play_set.all():
            if play != self and play.track == self.track:
                raise ValidationError(
                    '{track} already played during {show}.'.format(
                        track=self.track, show=self.show,
                    )
                )

    def save(self, *args, **kwargs):
        super(Play, self).save(*args, **kwargs)

        if self.track.hidden:
            self.track.hidden = False
            self.track.revealed = timezone.now()
            self.track.save()

    def tweet(self):
        """
        Send out a tweet for this play, set self.tweet_id and save.
        """

        if self.tweet_id is not None:
            raise TypeError('This play has already been tweeted')

        canon = str(self.track)
        hashtag = settings.HASHTAG

        if len(canon) > settings.TWEET_LENGTH - (len(hashtag) + 1):
            canon = canon[0:settings.TWEET_LENGTH-(len(hashtag)+2)]+u'…'

        status = u'%s %s' % (canon, hashtag)
        tweet = posting_tw_api.update_status(status)
        self.tweet_id = tweet.id
        self.save()

    tweet.alters_data = True

    def api_dict(self, verbose=False):
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

    def take_first_available_index(self):
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
    A request for a database addition. Stored for the benefit of enjoying
    hilarious spam.
    """

    METADATA_KEYS = ['trivia', 'trivia_question', 'contact']

    created = models.DateTimeField(auto_now_add=True)
    successful = models.BooleanField()
    blob = models.TextField()
    filled = models.DateTimeField(blank=True, null=True)
    filled_by = models.ForeignKey(User, blank=True, null=True,
                                  on_delete=models.SET_NULL)
    claimant = models.ForeignKey(
        User, blank=True, null=True, related_name='claims',
        on_delete=models.SET_NULL)
    track = models.ForeignKey(Track, blank=True, null=True,
                              on_delete=models.SET_NULL)

    def serialise(self, struct):
        self.blob = json.dumps(struct)

    def struct(self):
        return json.loads(self.blob)

    def non_metadata(self):
        return {
            k: v for k, v in self.struct().items()
            if (
                k not in Request.METADATA_KEYS or
                k == 'contact'
            ) and v.strip()
        }

    class Meta:
        ordering = ['-created']


class Note(CleanOnSaveMixin, models.Model):
    """
    A note about whatever for a particular track.
    """

    track = models.ForeignKey(Track, on_delete=models.CASCADE)
    show = models.ForeignKey(Show, blank=True, null=True,
                             on_delete=models.CASCADE)
    public = models.BooleanField(default=False)
    content = models.TextField()

    objects = NoteManager()

    def __str__(self):
        return self.content


class Badge(tuple):
    def __new__(cls, *args):
        return super(Badge, cls).__new__(cls, args)

    def info(self, user):
        slug, description, summary, icon, url, start, finish = self

        return {
            'slug': slug,
            'description': description.format(user=user),
            'summary': summary,
            'icon': icon,
            'url': url,
            'start': Show.at(start).showtime if start is not None else None,
            'finish': Show.at(finish).end if finish is not None else None,
        }


BADGES = [
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
        'likes of depriving people of sleep, fan of good mental health',
        'life-ring',
        'https://www.justgiving.com/fundraising/very-charity-scenario-2019',
        datetime.datetime(2019, 10, 1, tzinfo=get_default_timezone()),
        datetime.datetime(2019, 11, 27, tzinfo=get_default_timezone()),
    ),
    Badge(
        'charity-2020',
        u'{user.name} donated to the Very Scary Scenario charity streams '
        u'in 2020.',
        'likes depriving people of sleep, but somehow also likes bodily '
        'health',
        'heartbeat',
        'https://www.justgiving.com/fundraising/very-charity-scenario-2020',
        datetime.datetime(2020, 10, 1, tzinfo=get_default_timezone()),
        datetime.datetime(2020, 11, 27, tzinfo=get_default_timezone()),
    ),
]


class UserBadge(CleanOnSaveMixin, models.Model):
    badge = models.CharField(
        choices=[b[:2] for b in BADGES],
        max_length=max((len(b[0]) for b in BADGES)),
    )
    user = models.ForeignKey(TwitterUser, on_delete=models.CASCADE)

    @reify
    def badge_info(self):
        badge, = (b for b in BADGES if b[0] == self.badge)
        return badge.info(self.user)

    class Meta:
        unique_together = [['badge', 'user']]
