# -*- coding: utf-8 -*-

from cStringIO import StringIO
import datetime
import re
import json
from urlparse import urlparse

from cache_utils.decorators import cached
from dateutil import parser as date_parser
import requests
from PIL import Image, ImageFilter

from django.core.cache import cache
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile
from django.core.urlresolvers import resolve, Resolver404
from django.db import models
from django.utils import timezone
from django.template.defaultfilters import slugify
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.templatetags.static import static


from .managers import TrackManager, NoteManager
from .utils import (
    length_str, split_id3_title, vote_tweet_intent_url, reading_tw_api,
    posting_tw_api, memoize, pk_cached, indefinitely, lastfm, musicbrainzngs
)
from ..vote import mixcloud


class CleanOnSaveMixin(object):
    def save(self, force_save=False):
        if not force_save:
            self.full_clean()

        return super(CleanOnSaveMixin, self).save()


class SetShowBasedOnDateMixin(object):
    def save(self, force_save=False):
        self.show = Show.at(self.date)
        return super(CleanOnSaveMixin, self).save()


class Show(CleanOnSaveMixin, models.Model):
    """
    A broadcast of the show and, by extention, the week leading up to it.
    """

    showtime = models.DateTimeField(db_index=True)
    end = models.DateTimeField(db_index=True)

    def __str__(self):
        return '<Show for %r>' % (self.showtime.date())

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
    @cached(5)
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
    @cached(indefinitely)
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

    def _cache_if_not_current(self, func):
        if self == Show.current():
            return func(None)
        else:
            return cached(indefinitely)(func)(self.pk)

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
        return filter(lambda t: t not in self.playlist(),
                      [p.track for p in self.shortlist_set.all()])

    @memoize
    def discarded(self):
        return filter(lambda t: t not in self.playlist(),
                      [p.track for p in self.discard_set.all()])

    @memoize
    @pk_cached(20)
    def tracks_sorted_by_votes(self):
        """
        Return a list of tracks that have been voted for this week, in order of
        when they were last voted for, starting from the most recent.
        """

        track_set = set()
        tracks = []

        votes = Vote.objects.filter(
            show=self,
            twitter_user__is_abuser=False,
        ).prefetch_related('tracks').order_by('-date')

        for track in (
            track for vote in votes for track in vote.tracks.all()
        ):
            if track in track_set:
                continue

            track_set.add(track)
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

    def get_revealed_url(self):
        return reverse('vote:added', kwargs={
            'date': self.showtime.date().strftime('%Y-%m-%d')
        })

    def api_dict(self, verbose=False):
        prev = self.prev()
        if prev is None:
            start = None
        else:
            start = prev.end

        return {
            'playlist': [p.api_dict() for p in self.plays()],
            'added': [t.api_dict() for t in self.revealed()],
            'votes': [v.api_dict() for v in self.votes()],
            'showtime': self.showtime,
            'finish': self.end,
            'start': start,
        }


class TwitterUser(CleanOnSaveMixin, models.Model):
    # Twitter stuff
    screen_name = models.CharField(max_length=100)
    user_id = models.BigIntegerField(unique=True)
    user_image = models.URLField()
    name = models.CharField(max_length=20)

    # nkdsu stuff
    is_abuser = models.BooleanField(default=False)
    updated = models.DateTimeField()

    def __unicode__(self):
        return unicode(self.screen_name)

    def __repr__(self):
        return self.screen_name

    def twitter_url(self):
        return 'https://twitter.com/%s' % self.screen_name

    def get_absolute_url(self):
        return reverse('vote:user', kwargs={'screen_name': self.screen_name})

    def get_toggle_abuser_url(self):
        return reverse('vote:admin:toggle_abuser',
                       kwargs={'user_id': self.user_id})

    @memoize
    def votes(self):
        return self.vote_set.order_by('-date').prefetch_related('tracks')

    @memoize
    def votes_for(self, show):
        return self.votes().filter(show=show)

    @memoize
    def tracks_voted_for_for(self, show):
        tracks = set()

        for vote in self.votes_for(show):
            for track in vote.tracks.all():
                tracks.add(track)

        return tracks

    def _batting_average(self, cutoff=None, minimum_weight=1):
        @cached(indefinitely)
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

    def _streak(self, l=[]):
        show = Show.current().prev()
        streak = 0

        while True:
            if show.votes().filter(twitter_user=self).exists():
                streak += 1
                show = show.prev()
            else:
                break

        return streak

    @memoize
    def streak(self):
        @cached(indefinitely)
        def streak(pk, current_show):
            return self._streak()

        return streak(self.pk, Show.current())

    def all_time_batting_average(self, minimum_weight=1):
        return self._batting_average(minimum_weight=minimum_weight)

    def update_from_api(self):
        """
        Update this user's database object based on the Twitter API.
        """

        api_user = reading_tw_api.get_user(user_id=self.user_id)

        self.name = api_user.name
        self.screen_name = api_user.screen_name
        self.user_image = api_user.profile_image_url
        self.updated = timezone.now()

        self.save()


class Track(CleanOnSaveMixin, models.Model):
    objects = TrackManager()

    # derived from iTunes
    id = models.CharField(max_length=16, primary_key=True)
    id3_title = models.CharField(max_length=500)
    id3_artist = models.CharField(max_length=500)
    id3_album = models.CharField(max_length=500, blank=True)
    msec = models.IntegerField(blank=True, null=True)
    added = models.DateTimeField()

    # nkdsu-specific
    revealed = models.DateTimeField(blank=True, null=True)
    hidden = models.BooleanField()
    inudesu = models.BooleanField()
    background_art = models.ImageField(
        blank=True, upload_to=lambda i, f: 'art/bg/%s.%s'
        % (i.pk, f.split('.')[-1]))

    def __unicode__(self):
        """
        The string that, for instance, would be tweeted
        """

        if self.role:
            return u'‘%s’ (%s) - %s' % (self.title, self.role, self.artist)
        else:
            return u'‘%s’ - %s' % (self.title, self.artist)

    def __eq__(self, other):
        return type(self) == type(other) and self.id == other.id

    def clean(self):
        if (not self.inudesu) and (not self.hidden) and (not self.revealed):
            raise ValidationError('{track} is not hidden but has no revealed '
                                  'date'.format(track=self))

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

        return (show.end - self.last_play().date).days / 7

    @property
    def title(self):
        return self.split_id3_title()[0]

    @property
    def album(self):
        return self.id3_album

    @property
    def role(self):
        return self.split_id3_title()[1]

    @property
    def artist(self):
        return self.id3_artist

    @memoize
    def artist_names(self):
        artist_string = self.artist
        separator = ', '
        ultimate_separator = ' and '
        if ultimate_separator not in artist_string:
            return [artist_string]
        else:
            ultimate_split = artist_string.split(ultimate_separator)
            last_artist = ultimate_split[-1]
            pre_ultimate = ultimate_separator.join(ultimate_split[:-1])
            everyone_else = pre_ultimate.split(separator)
            return everyone_else + [last_artist]

    @memoize
    @pk_cached(90)
    def artists(self):
        return [
            {
                'url': reverse('vote:artist', kwargs={'artist': name}),
                'name': name,
                'worth_showing': bool(
                    Track.objects.by_artist(name)
                )
            }
            for name in self.artist_names()
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

        current_show = Show.current()
        block_qs = current_show.block_set.filter(track=self)

        if self.inudesu:
            reason = 'inu desu'

        elif self.hidden:
            reason = 'hidden'

        elif self.play_set.filter(show=current_show).exists():
            reason = 'played this week'

        elif self.play_set.filter(show=current_show.prev()).exists():
            reason = 'played last week'

        elif block_qs.exists():
            reason = block_qs.get().reason

        else:
            reason = False

        return reason

    @memoize
    @pk_cached(10)
    def votes_for(self, show):
        """
        Return votes for this track for a given show.
        """

        return self.vote_set.filter(show=show).order_by('date')

    @memoize
    def notes(self):
        return self.note_set.for_show_or_none(Show.current)

    @memoize
    def public_notes(self):
        return self.note_set.for_show_or_none(Show.current).filter(public=True)

    def play(self):
        """
        Mark this track as played.
        """

        play = Play(
            track=self,
            date=timezone.now(),
        )

        play.save()
        play.tweet()

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

    def slug(self):
        return slugify(self.title)

    def get_absolute_url(self):
        return reverse('vote:track', kwargs={'slug': self.slug(),
                                             'pk': self.pk})

    def get_public_url(self):
        return 'http://nkd.su' + self.get_absolute_url()

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

        input_image = Image.open(StringIO(requests.get(image_url).content))

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
            'artist': self.artist,
            'length': self.msec,
            'inu desu': self.inudesu,
            'url': self.get_public_url(),
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
)


class Vote(SetShowBasedOnDateMixin, CleanOnSaveMixin, models.Model):
    # universal
    tracks = models.ManyToManyField(Track, db_index=True)
    date = models.DateTimeField(db_index=True)
    show = models.ForeignKey(Show, related_name='vote_set')
    text = models.TextField(blank=True)

    # twitter only
    twitter_user = models.ForeignKey(TwitterUser, blank=True, null=True,
                                     db_index=True)
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

        if 'text' not in tweet:
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
        twitter_user.user_image = tweet['user']['profile_image_url']
        twitter_user.updated = created_at
        twitter_user.save()

        tracks = []
        for url in tweet['entities']['urls']:
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

                if (
                    track not in twitter_user.tracks_voted_for_for(show) and
                    track.eligible()
                ):
                    tracks.append(track)

        if tracks:
            vote = cls(
                tweet_id=tweet['id'],
                twitter_user=twitter_user,
                date=created_at,
                text=tweet['text'],
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

    @property
    def is_manual(self):
        return not bool(self.tweet_id)

    def get_image_url(self):
        if self.is_manual:
            return static('i/vote-kinds/{0}.png'.format(self.kind))
        else:
            return self.twitter_user.user_image

    def __unicode__(self):
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
            if content.startswith('@'):
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
                'user_name': self.twitter_user.name,
                'user_screen_name': self.twitter_user.screen_name,
                'user_image': self.twitter_user.user_image,
                'user_id': self.twitter_user.user_id,
                'tweet_id': self.tweet_id,
            })

        return the_vote

    def twitter_url(self):
        return 'http://twitter.com/%s/status/%s/' % (
            self.twitter_user.screen_name,
            self.tweet_id,
        )


class Play(SetShowBasedOnDateMixin, CleanOnSaveMixin, models.Model):
    date = models.DateTimeField(db_index=True)
    show = models.ForeignKey(Show)
    track = models.ForeignKey(Track, db_index=True)
    tweet_id = models.BigIntegerField(blank=True, null=True)

    def __unicode__(self):
        return u'%s at %s' % (self.track, self.date)

    def clean(self):
        if not settings.DEBUG:
            if (not self.show().broadcasting(self.date)):
                raise ValidationError('It is not currently showtime.')

        if self.track in self.show().playlist():
            raise ValidationError(
                '{track} already played during {show}.'.format(
                    track=self.track, show=self.show(),
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

        canon = unicode(self.track)
        hashtag = settings.HASHTAG

        if len(canon) > 140 - (len(hashtag) + 1):
            canon = canon[0:140-(len(hashtag)+2)]+u'…'

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

    track = models.ForeignKey(Track)
    reason = models.CharField(max_length=256)
    show = models.ForeignKey(Show)

    class Meta:
        unique_together = [['show', 'track']]


class Shortlist(CleanOnSaveMixin, models.Model):
    show = models.ForeignKey(Show)
    track = models.ForeignKey(Track)
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

    show = models.ForeignKey(Show)
    track = models.ForeignKey(Track)

    class Meta:
        unique_together = [['show', 'track']]


class Request(CleanOnSaveMixin, models.Model):
    """
    A request for a database addition. Stored for the benefit of enjoying
    hilarious spam.
    """

    created = models.DateTimeField(auto_now_add=True)
    successful = models.BooleanField()
    blob = models.TextField()

    def serialise(self, struct):
        self.blob = json.dumps(struct)

    def struct(self):
        return json.loads(self.blob)


class Note(CleanOnSaveMixin, models.Model):
    """
    A note about whatever for a particular track.
    """

    track = models.ForeignKey(Track)
    show = models.ForeignKey(Show, blank=True, null=True)
    public = models.BooleanField(default=False)
    content = models.TextField()

    objects = NoteManager()

    def __unicode__(self):
        return self.content
