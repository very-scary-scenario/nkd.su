# -*- coding: utf-8 -*-

import datetime
import re
import json

from django.db import models
from django.utils import timezone
from django.template.defaultfilters import slugify
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse

from vote.utils import (length_str, split_id3_title, vote_tweet_intent_url,
                        reading_tw_api)


class Show(models.Model):
    """
    A broadcast of the show and, by extention, the week leading up to it.
    """

    showtime = models.DateTimeField()
    end = models.DateTimeField()

    def __str__(self):
        return '<Show for %r>' % (self.showtime.date())

    def __repr__(self):
        return str(self)

    @classmethod
    def current(cls):
        """
        Get (or create, if necessary) the show that will next end.
        """

        return cls.show_for(timezone.now())

    @classmethod
    def at(cls, time):
        """
        Get (or create, if necessary) the show for `time`.
        """

        if time > timezone.now():
            raise NotImplementedError('Cannot be called with dates falling '
                                      'in the future.')

        shows_after_time = cls.objects.filter(end__gte=time)
        if shows_after_time.exists():
            show = shows_after_time.order_by('showtime')[0]
        else:
            # We have to switch to naive and back to make relativedelta
            # look for the local showtime. If we did not, showtime would be
            # calculated against UTC.
            # Note that this could be a problem if a show is ever scheduled for
            # a time that does not exist. If you're planning one, be sure to
            # explicitly set which side of the clocks changing the show will be
            # hosted at least a week in advance, or the site will start 500ing
            # the moment the previous show ends.
            naive_time = timezone.make_naive(time,
                                             timezone.get_current_timezone())
            naive_end = naive_time + settings.SHOW_END

            # work around an unfortunate shortcoming of dateutil where
            # specifying a time on a weekday won't increment the weekday even
            # if our initial time is after that time
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
    def broadcasting_now(cls):
        """
        Return True if a show is broadcasting.
        """

        return cls.current().broadcasting(timezone.now())

    def broadcasting(self, time=None):
        """
        Return True if the time specified is during this week's show.
        """

        return (time >= self.showtime) and (time < self.finish)

    def next(self, ideal=False):
        """
        Return the next Show
        """

        # XXX

    def prev(self, ideal=False):
        """
        Return the previous Show
        """

        # XXX

    def tracks_sorted_by_votes(self, exclude_abusers=False):
        """
        Return a list of tracks that have been voted for this week, in order of
        when they were last voted for, starting from the most recent.
        """

        # XXX

    def added(self, show_hidden=False):
        """
        Return a all public (unhidden, non-inudesu) tracks added to the library
        this week.
        """

        # XXX

    def get_absolute_url(self):
        return reverse('show', kwargs={'date': self.showtime.date()})

    def get_added_url(self):
        return reverse('added', kwargs={'date': self.showtime.date()})


class TwitterUser(models.Model):
    # Twitter stuff
    screen_name = models.CharField(max_length=100)
    id = models.IntegerField(primary_key=True)
    user_image = models.URLField()
    name = models.CharField(max_length=20)

    # nkdsu stuff
    is_abuser = models.BooleanField(default=False)
    updated = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return unicode(self.screen_name)

    def __repr__(self):
        return self.screen_name

    def twitter_url(self):
        return 'https://twitter.com/%s' % self.screen_name

    def get_absolute_url(self):
        return reverse('user', kwargs={'screen_name': self.screen_name})

    def batting_average(self, cutoff=None):
        """
        Return a user's batting average for shows after cutoff. If cutoff is
        None, assume the beginning of time.
        """

        # XXX

    def update_from_api(self):
        """
        Update this user's database object based on the Twitter API.
        """

        api_resp = reading_tw_api.get_user(screen_name=self.id)
        print api_resp

        # XXX actually do the thing


class Track(models.Model):
    id = models.CharField(max_length=16, primary_key=True)

    id3_title = models.CharField(max_length=500)
    title_en = models.CharField(max_length=500, blank=True)
    title_ro = models.CharField(max_length=500, blank=True)
    title_ka = models.CharField(max_length=500, blank=True)
    id3_artist = models.CharField(max_length=500)
    id3_album = models.CharField(max_length=500, blank=True)
    show_en = models.CharField(max_length=500, blank=True)
    show_ro = models.CharField(max_length=500, blank=True)
    show_ka = models.CharField(max_length=500, blank=True)
    role = models.CharField(max_length=100, blank=True)
    msec = models.IntegerField(blank=True, null=True)
    added = models.DateTimeField(blank=True, null=True)
    hidden = models.BooleanField()
    inudesu = models.BooleanField()

    def __unicode__(self):
        """
        The string that, for instance, would be tweeted
        """

        if self.role:
            return u'‘%s’ (%s) - %s' % (self.title, self.role, self.id3_artist)
        else:
            return u'‘%s’ - %s' % (self.title, self.id3_artist)

    def __eq__(self, other):
        return type(self) == type(other) and self.id == other.id

    def is_new(self, time=None):
        return self.added > self.current_week(time).start and (
            not self.last_played())

    def length_str(self):
        return length_str(self.msec)

    def weeks_since_play(self, time=None):
        """
        Get the number of shows that have ended since this track's most recent
        Play.
        """

        # XXX

    def undoable(self):
        """
        Return True if this track is the source of the most recent Play.
        Criteria subject to change.
        """

        return Play.objects.all().order_by('-datetime')[0].track == self

    def block(self, show):
        """
        Get any block from the week specified applying to this Track in the
        specified show.
        """

        # XXX

    @property
    def title(self):
        return self.split_id3_title()[0]

    @property
    def role(self):
        return self.split_id3_title()[1]

    @property
    def artist(self):
        return self.id3_artist

    def split_id3_title(self):
        return split_id3_title(self.id3_title)

    def artist_has_page(self):
        """
        Return True if this artist has an artist page worth showing.
        """

        return Track.objects.filter(
            id3_artist=self.id3_artist, hidden=False, inudesu=False).exists()

    def deets(self):
        """
        Return a more detailed string
        """

        return ('%s: %s - %s - %s - %i msec - %s'
                % (self.id, self.id3_title, self.id3_artist, self.id3_album,
                   self.msec, self.added))

    def eligible(self):
        """
        Returns True if this track can be requested.
        """

        return not self.ineligible()

    def ineligible(self):
        """
        Return a string describing why a track is ineligible, or False if it
        is not
        """

        # XXX gonna break, but shouldn't be difficult to fix

        week = self.current_week()

        if self.inudesu:
            self.reason = 'inu desu'

        elif self.hidden:
            self.reason = 'hidden'

        elif week.plays(self, select_related=False).exists():
            self.reason = 'played this week'

        elif week.prev().plays(self).filter(track=self):
            self.reason = 'played last week'

        elif self.block(week):
            self.reason = self.block(week).reason

        else:
            self.reason = False

        return self.reason

    def shortlist(self, time=None):
        """
        Shortlist this track for this week.
        """

        # XXX

    def discard(self, time=None):
        """
        Discard this track for this week.
        """

        # XXX

    def slug(self):
        return slugify(self.title)

    def get_absolute_url(self):
        return reverse('track_by_slug', kwargs={'slug': self.slug(),
                                                'track_id': self.id})

    def public_url(self):
        return 'http://nkd.su' + self.rel_url()

    def report_url(self):
        return reverse('report', kwargs={'track_id': self.id})

    def vote_url(self):
        """
        Return the Twitter intent url for voting for this track alone.
        """

        return vote_tweet_intent_url([self])

    def api_dict(self, verbose=False):
        the_track = {
            'id': self.id,
            'title': self.derived_title(),
            'role': self.derived_role(),
            'artist': self.id3_artist,
            'length': self.msec,
            'inu desu': self.inudesu,
            'url': self.url(),
        }

        if verbose:
            the_track.update({
                'plays': [p.datetime for p in Play.objects.filter(track=self)]
            })

        return the_track


MANUAL_VOTE_KINDS = (
    ('email', 'email'),
    ('text', 'text'),
    ('tweet', 'tweet'),
)


class Vote(models.Model):
    # universal
    tracks = models.ManyToManyField(Track)
    date = models.DateTimeField()
    show = models.ForeignKey(Show)
    text = models.TextField(blank=True)

    # twitter only
    twitter_user = models.ForeignKey(TwitterUser, blank=True)
    tweet_id = models.IntegerField()

    # manual only
    name = models.CharField(max_length=40)
    kind = models.CharField(max_length=10, choices=MANUAL_VOTE_KINDS)

    @property
    def is_manaul(self):
        return not self.kind

    def __unicode__(self):
        pass  # XXX

    def derive_tracks_from_url_list(self, url_list):
        """
        Take a list of URLs and return a list of Tracks that should be
        considered voted for based on that list.
        """

        # XXX should be fine, but might want to make a little DRYer

        tracks = []
        for url in url_list:
            chunks = url.strip('/').split('/')
            track_id = chunks[-1]
            slug = chunks[-2]
            try:
                track = Track.objects.get(id=track_id)
            except Track.DoesNotExist:
                pass
            else:
                if track.slug() == slug:
                    tracks.append(track)

        return tracks

    def content(self):
        """
        Return the non-mention, non-url content of the text.
        """

        content = self.text.replace('@%s' %
                                    settings.READING_USERNAME, '').strip('- ')
        for word in content.split():
            if re.match(r'https?://[^\s]+', word):
                content = content.replace(word, '').strip()
            elif len(word) == 16 and re.match('[0-9A-F]{16}', word):
                # for the sake of old pre-url votes
                content = content.replace(word, '').strip()

        return content

    def relevant_prior_voted_tracks(self):
        """
        Return the tracks that this vote's issuer has already voted for this
        show.
        """

        # XXX

    def clean(self):
        # XXX require that manual votes have a type and twitter votes have
        # a user

        # XXX Be xor-y (that is, don't allow twitter votes to have manual vote
        # properties and vice-versa)

        if not self.tracks:
            raise ValidationError('no tracks in vote')

    def api_dict(self):
        the_vote = {
            'user_name': self.name,
            'user_screen_name': self.screen_name,
            'user_image': self.user_image,
            'user_id': self.user_id,
            'tweet_id': self.tweet_id,
            'comment': self.content() if self.content() != '' else None,
            'time': self.date,
            'track_ids': [t.id for t in self.get_tracks()],
            'tracks': [t.api_dict() for t in self.get_tracks()]
        }

        return the_vote

    def twitter_url(self):
        return 'http://twitter.com/%s/status/%s/' % (self.user.screen_name,
                                                     self.user.tweet_id)


class Play(models.Model):
    datetime = models.DateTimeField()
    track = models.ForeignKey(Track)
    tweet_id = models.IntegerField(blank=True, null=True)
    show = models.ForeignKey(Show)

    def __str__(self):
        return '<played %s at %s>' % (self.track, self.datetime)

    def clean(self):
        if (not Show.was_broadcasting(self.datetime)):
            raise ValidationError('It is not currently showtime.')

        # XXX raise ValidationError('This has been played today already.')

        self.track.hidden = False  # If something's been played, it's public.
        self.track.save()


class Block(models.Model):
    """
    A particular track that we are not going to allow to be voted for on
    particular show.
    """

    track = models.ForeignKey(Track)
    reason = models.CharField(max_length=256)
    show = models.ForeignKey(Show)

    # XXX unique_together show and track

    def clean(self):
        if self.track.ineligible():
            raise ValidationError('track is already blocked')


class Shortlist(models.Model):
    show = models.ForeignKey(Show)
    track = models.ForeignKey(Track)
    index = models.IntegerField(default=0)

    # XXX unique_together show and track

    def save(self):
        pass  # XXX set our index appropriately


class Discard(models.Model):
    """
    A track that we're not going to play, but that we don't want to make public
    that we're not going to play.
    """

    show = models.ForeignKey(Show)
    track = models.ForeignKey(Track)
    # XXX unique_together show and track


class Request(models.Model):
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
