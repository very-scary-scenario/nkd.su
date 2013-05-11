# -*- coding: utf-8 -*-

import datetime
import re
import json

from django.db import models
from django.utils import timezone
from django.template.defaultfilters import slugify
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.http import urlquote
from django.http import Http404
from django.core.urlresolvers import reverse

import tweepy

post_tw_auth = tweepy.OAuthHandler(settings.CONSUMER_KEY,
                                   settings.CONSUMER_SECRET)
post_tw_auth.set_access_token(settings.READING_ACCESS_TOKEN,
                              settings.READING_ACCESS_TOKEN_SECRET)
tw_api = tweepy.API(post_tw_auth)


def latest_play(track=None):
    """ Get the latest play (for a particular track). """
    plays = Play.objects.all()

    if track:
        plays = plays.filter(track=track)

    return plays.order_by('-datetime')[0]


def total_length(tracks):
    return sum([t.msec for t in tracks])


def length_str(msec):
    seconds = msec/1000
    remainder_seconds = seconds % 60
    minutes = (seconds - remainder_seconds) / 60

    if minutes >= 60:
        remainder_minutes = minutes % 60
        hours = (minutes - remainder_minutes) / 60
        return '%i:%02d:%02d' % (hours, remainder_minutes, remainder_seconds)
    else:
        return '%i:%02d' % (minutes, remainder_seconds)


def now_or_time(time):
    """ Returns datetime.now() if time is False, otherwise returns time """
    if time:
        return time
    else:
        return datetime.datetime.utcnow().replace(tzinfo=timezone.utc)


def is_on_air(time=None):
    """ Returns True if there's a broadcast on"""
    return Week(now_or_time(time), ignore_apocalypse=True).is_on_air(time)


def when(date):
    """
    Return a nice, human-readable date.
    """

    our_day = date.date()
    today = timezone.now().date()
    if our_day == today:
        return date.strftime('%I:%M %p').lower()
    elif today - our_day <= datetime.timedelta(days=6):
        return date.strftime('%A at %I:%M %p').lower()
    else:
        return date.strftime('%a %b %d at %I:%M %p').lower()


class Week(object):
    """ A week. Cut off at the end of each broadcast """
    def __str__(self):
        return '<week of %r>' % (self.showtime.date())

    def __repr__(self):
        return str(self)

    showtime_day = 5  # saturday
    start_hour = 21
    end_hour = 23
    target_tuple = (end_hour, 0, 0, showtime_day)
    target_showtime_tuple = (start_hour, 0, 0, showtime_day)
    show_locale = timezone.get_current_timezone()

    def _approach(self, time, target_tuple, forwards):
        """
        Approach a given time one hour at a time until the time matches the
        target_tuple in hours
        """

        one_hour = datetime.timedelta(hours=1)

        while time.astimezone(
                self.show_locale).timetuple()[3:7] != target_tuple:
            if forwards:
                time = time + one_hour
            else:
                time = time - one_hour

        return time

    def __init__(self, time=None, correct=True, ignore_apocalypse=True,
                 ideal=False):
        """ Create the Week in which time (or now) resides.

        If correct is True, (which it is by default), we'll correct for
        overridden times by choosing the next or previous week.

        If ignore_apocalypse is False, this week will become next week if the
        apocalypse happened.

        If ideal is True, the database is totally ignored. """

        time = now_or_time(time)

        one_hour = datetime.timedelta(hours=1)

        # set up default values
        start = self._round_down_to_hour(time)
        start = self._approach(start, self.target_tuple, False)
        finish = self._approach(start + one_hour, self.target_tuple, True)
        showtime = self._approach(finish - one_hour,
                                  self.target_showtime_tuple, False)

        # necessary to do now for self.prev() to work
        self._prev_week_default_showtime = self._approach(
            start, self.target_showtime_tuple, False)
        self._next_week_default_showtime = self._approach(
            finish, self.target_showtime_tuple, True)

        if not ideal:
            # is this week's start time to be overridden? (ie. was last week's
            # finish time modified)
            try:
                ScheduleOverride.objects.get(
                    overridden_showdate=self._prev_week_default_showtime)
            except ScheduleOverride.DoesNotExist:
                # nope
                pass
            else:
                # yep
                start = self.prev().finish

            # are this week's showtime and finish to be overridden?
            try:
                this_override = ScheduleOverride.objects.get(
                    overridden_showdate=showtime.date())
            except ScheduleOverride.DoesNotExist:
                # nope
                pass
            else:
                # yep
                finish = this_override.finish
                showtime = this_override.start

        self.start = start
        self.finish = finish
        self.showtime = showtime

        self.date_range = [self.start, self.finish]
        self.vote_date_range = [self.start, self.finish]

        # do we actually fall into this range? if not, we should try again
        # we del self._prev because we set it when we realised the time had to
        # be overridden
        # note that 'correct' here is a verb, an instruction; not an adjective
        if (not ideal) and correct:
            if time > self.finish:
                del self._prev
                self = self.__init__(self._next_week_default_showtime,
                                     correct=False)
                return
            elif time < self.start:
                del self._prev
                self = self.__init__(self._prev_week_default_showtime,
                                     correct=False)
                return
                # and don't do anything else; the rest of this function will be
                # handled in the  __init__ we just called

        if not ideal:
            # is there a robot apocalypse this week?
            if self.has_robot_apocalypse():
                # we care about this week for archives, but not for most of the
                # rest of the time
                if not ignore_apocalypse:
                    self = self.__init__(self._next_week_default_showtime)
                    return  # we're done here

            # how about last week?
            elif self.last_week_has_robot_apocalypse():
                # there was there a robot apocalypse last week. was there one
                # the week before that?  if this is a legit week, we always
                # care; votes gathered are important regardless of context

                showdate_rollback = self._prev_week_default_showtime
                while RobotApocalypse.objects.filter(
                        overridden_showdate=showdate_rollback).exists():
                    showdate_rollback -= datetime.timedelta(days=7)
                else:
                    # okay, so the one we want was the last one
                    showdate_rollback += datetime.timedelta(days=7)

                self.vote_date_range = [Week(showdate_rollback,
                                             ideal=True).start, self.finish]

    def __eq__(self, other):
        return self.showtime == other.showtime

    def __ne__(self, other):
        return not self == other

    def _round_down_to_hour(self, time):
        """ Rounds time down to the nearest hour """
        delta = datetime.timedelta(minutes=time.minute, seconds=time.second,
                                   microseconds=time.microsecond)
        return time - delta

    def is_on_air(self, time=None):
        """
        Returns True if the time specified (or now) is during this week's
        broadcast
        """

        time = now_or_time(time)
        return (time >= self.showtime) and (time < self.finish)

    def next(self, ideal=False):
        if ideal:
            return Week(self._next_week_default_showtime, correct=False,
                        ideal=True)
        else:
            try:
                return self._next
            except AttributeError:
                pass

            self._next = Week(self._next_week_default_showtime, correct=False)
            self._next._prev = self
            return self._next

    def prev(self, ideal=False):
        """ Returns the previous Week. See also: next(). """
        if ideal:
            return Week(self._prev_week_default_showtime, correct=False,
                        ideal=True)
        else:
            try:
                return self._prev
            except AttributeError:
                pass

            self._prev = Week(self._prev_week_default_showtime, correct=False)
            self._prev._next = self
            return self._prev

    def has_robot_apocalypse(self, cache=True):
        if RobotApocalypse.objects.filter(
                overridden_showdate=self.showtime.date()).exists():
            return True
        else:
            return False

    def last_week_has_robot_apocalypse(self):
        if RobotApocalypse.objects.filter(
            overridden_showdate=self._prev_week_default_showtime.date()
        ).exists():
            return True
        else:
            return False

    def has_plays(self):
        """ True if this week has any plays  """
        return self.plays().exists()

    def tracks_played(self):
        try:
            return self._tracks_played
        except AttributeError:
            self._tracks_played = [p.track for p in self.plays()]
            return self._tracks_played

    def plays(self, track=None, invert=False, select_related=False):
        """
        Returns all plays, in chronological order, from this Week's show as a
        QuerySet.

        If track is specified, gets plays of that track
        """

        if invert:
            order = '-datetime'
        else:
            order = 'datetime'

        plays = Play.objects.filter(
            datetime__range=self.date_range).order_by(order)

        if track:
            plays = plays.filter(track=track)
        if select_related:
            plays = plays.select_related()

        return plays

    def _shortlist_or_discard(self, track, c):
        """
        Does the actual work for shortlist() and discard()

        c is the class to use
        """

        if track:
            try:
                return c.objects.get(date__range=self.date_range, track=track)
            except c.DoesNotExist:
                return None
        else:
            tracks = [s.track for s in c.objects.filter(
                date__range=self.date_range)]
            # to prevent redundant Week creation
            [setattr(t, '_vote_week', self) for t in tracks]
            [setattr(t, '_current_week', self) for t in tracks]
            return tracks

    def shortlist(self, track=None):
        """
        Return a list of shortlisted tracks

        if track is specified, return its Shortlist object for this week if
        present or None
        """

        return self._shortlist_or_discard(track, Shortlist)

    def discard(self, track=None):
        """ Like shortlist(), but for discards """
        return self._shortlist_or_discard(track, Discard)

    def shortlist_or_discard(self, track):
        """
        Return a shortlist or discard if there are shortlists or discards on
        this track this week, otherwise return False
        """

        discard = self.discard(track)
        if discard:
            return discard
        shortlist = self.shortlist(track)
        if shortlist:
            return shortlist

        return False

    def tracks_sorted_by_votes(self):
        votes = self.votes()
        track_dict = {}

        # we need the track dict to be persistent so that stuff that is
        # cacheable stays cached
        [track_dict.__setitem__(t.id, t)
         for v in votes for t in v.get_tracks()]

        vote_dict = {}
        for vote in votes:
            for track in vote.get_tracks():
                # to prevent redundant Week creation
                track._vote_week = self
                track._current_week = self

                if track.id not in vote_dict:
                    vote_dict[track.id] = vote.date
                elif vote.date > vote_dict[track.id]:
                    vote_dict[track.id] = vote.date

        return sorted(track_dict.values(), reverse=True,
                      key=lambda t: vote_dict[t.id])

    def votes(self, track=None):
        """
        Get all votes of any kind (for a particular track) from this week
        """

        votes, manual_votes = self.votes_in_a_tuple(track=track)
        return list(votes) + list(manual_votes)

    def votes_in_a_tuple(self, track=None):
        """
        Returns all Votes and ManualVotes from this week in a tuple of
        QuerySets

        If track is specified, filters by track
        """

        try:
            return self.vote_tuple_cache
        except AttributeError:
            pass

        votes = self._votes(track)
        manual_votes = self._manual_votes(track)
        self.vote_tuple_cache = (votes, manual_votes)

        return self.vote_tuple_cache

    def _manual_votes(self, track=None):
        if self.has_robot_apocalypse():
            return []

        manual_votes = ManualVote.objects.filter(
            date__range=self.vote_date_range).order_by('date')

        if track:
            manual_votes = manual_votes.filter(track=track)
        else:
            manual_votes.select_related()

        return manual_votes

    def _votes(self, track=None):
        if self.has_robot_apocalypse():
            return []

        votes = Vote.objects.filter(
            date__range=self.vote_date_range).order_by('date')

        if track:
            votes = votes.filter(tracks=track)
        else:
            votes.select_related()

        return votes

    def added(self, show_hidden=False):
        """
        Return a QuerySet of all (unhidden, non-inudesu) tracks added to the
        library this week.
        """

        tracks = Track.objects.filter(added__range=self.date_range,
                                      inudesu=False)

        if not show_hidden:
            tracks = tracks.filter(hidden=False)

        return tracks

    def count_votes(self):
        """
        Return the number of votes, counting a vote for n tracks as n votes.
        """

        return len([t for v in self.votes() for t in v.get_tracks()])

    def count_voters(self):
        """
        Return the number of unique voters this week.
        """

        twitter_voters = [v.user_id for v in self._votes()]
        manual_voters = [v.name for v in self._manual_votes()]

        return len(set(twitter_voters + manual_voters))

    def get_absolute_url(self):
        return reverse('show', kwargs={'date': self.showtime.date()})

    def get_added_url(self):
        return reverse('added', kwargs={'date': self.showtime.date()})


class User(object):
    """ A twitter user """
    def __unicode__(self):
        return self.screen_name()

    def __repr__(self):
        return self.screen_name()

    def __init__(self, user_id):
        try:
            user_id = int(user_id)
        except ValueError:
            try:
                user_id = tw_api.get_user(screen_name=user_id).id
            except tweepy.TweepError:
                raise Http404

        self.id = user_id

    def votes(self, week=None):
        if week:
            return week._votes().filter(user_id=self.id)
        else:
            try:
                return self._votes
            except AttributeError:
                self._votes = Vote.objects.filter(
                    user_id=self.id).order_by('-date')
                return self._votes

    def vote_weeks(self, week=None):
        votes = self.votes()

        vote_weeks = []
        for vote in votes:
            if vote.get_tracks():
                if not vote_weeks or vote.date < vote_weeks[-1][0].start:
                    vote_weeks.append((vote.week(), []))

                append = vote_weeks[-1][1].append

                append(vote)

        return vote_weeks

    def most_recent_vote(self):
        try:
            return self._most_recent_vote
        except AttributeError:
            self._most_recent_vote = self.votes().order_by('-date')[0]
            return self._most_recent_vote

    def twitter_url(self):
        return 'https://twitter.com/%s' % self.screen_name()

    def get_absolute_url(self):
        return reverse('user', kwargs={'screen_name': self.screen_name()})

    def batting_average(self):
        try:
            return self._batting_average
        except AttributeError:
            pass

        successes = 0.
        failures = 0.
        this_week = Week()
        week = this_week.prev()

        for vote in self.votes().filter(date__lt=this_week.start):
            if vote.date < week.start:
                # we're looking at votes for the previous week now
                week = vote.week()

            print vote.date
            if vote.date > week.finish:
                print '## clearly something went wrong here'

            for track in vote.get_tracks():
                if track in week.tracks_played():
                    print 'SUCCESS %s' % track
                    successes += 1
                else:
                    print 'failure %s' % track
                    failures += 1

        try:
            avg = successes / (successes + failures)
        except ZeroDivisionError:
            return '[in flux]%'
        avg *= 100

        self._batting_average = '%i%%' % avg
        return self._batting_average

    @classmethod
    def create_alias(cls, attrib):
        func = lambda self: getattr(self.most_recent_vote(), attrib)
        setattr(cls, attrib, func)


for attrib in ['screen_name', 'name', 'user_image']:
    User.create_alias(attrib)


def vote_tweet(tracks):
    return '@%s %s' % (settings.READING_USERNAME,
                       ' '.join([t.url() for t in tracks]))


def tweet_url(tweet):
    return 'https://twitter.com/intent/tweet?text=%s' % urlquote(tweet)


def vote_url(tracks):
    return tweet_url(vote_tweet(tracks))


def tweet_len(tweet):
    placeholder_url = ''
    while len(placeholder_url) < settings.TWITTER_SHORT_URL_LENGTH:
        placeholder_url = placeholder_url + 'x'

    shortened = re.sub('https?://[^\s]+', placeholder_url, tweet)
    return len(shortened)


def split_id3_title(id3_title):
    """ Split a Title (role) ID3 title, return title, role """
    role = None

    bracket_depth = 0
    for i in range(1, len(id3_title)+1):
        char = id3_title[-i]
        if char == ')':
            bracket_depth += 1
        elif char == '(':
            bracket_depth -= 1

        if bracket_depth == 0:
            if i != 1:
                role = id3_title[len(id3_title)-i:]
            break

    if role:
        title = id3_title.replace(role, '').strip()
        role = role[1:-1]  # strip brackets
    else:
        title = id3_title

    return title, role


class Track(models.Model):
    def __unicode__(self):
        return self.canonical_string()

    def __eq__(self, other):
        return type(self) == type(other) and self.id == other.id

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

    def is_new(self, time=None):
        return self.added > self.current_week(time).start and (
            not self.last_played())

    def length_str(self):
        return length_str(self.msec)

    def last_played(self):
        """ Get the datetime of this track's most recent play """
        try:
            return self.last_play().datetime
        except AttributeError:
            return None

    def last_played_showtime(self):
        current_week = self.current_week()
        last_played = self.last_played()
        while current_week.start > last_played:
            current_week = current_week.prev()
        return current_week.showtime

    def last_play(self):
        """ Get the datetime this track's most recent Play """
        try:
            return self.last_play_cache
        except AttributeError:
            pass

        try:
            last_play = Play.objects.filter(track=self).order_by(
                '-datetime')[0]
        except IndexError:
            last_play = None

        self.last_play_cache = last_play
        return self.last_play_cache

    def weeks_since_play(self, time=None):
        """
        Get the number of shows that have ended since this track's most recent
        Play.
        """

        try:
            return self._weeks_since_play
        except AttributeError:
            pass

        time = now_or_time(time)
        this_week = self.current_week(time)
        last_play = self.last_play()
        if last_play is None:
            return None

        # prevent infinite loops, just in case
        assert time > last_play.datetime

        weeks_ago = 0
        working_week = this_week

        while last_play.datetime < working_week.showtime:
            working_week = working_week.prev()
            weeks_ago += 1

        self._weeks_since_play = weeks_ago
        return weeks_ago

    def undoable(self):
        """
        Return True if this track is the source of the most recent Play.
        Criteria subject to change.
        """

        return Play.objects.all().order_by('-datetime')[0].track == self

    def block(self, week=None):
        """ Get any block from the week specified """
        week = self.current_week()

        try:
            return self._block[week]
        except AttributeError:
            self._block = {}
        except KeyError:
            pass

        try:
            block = Block.objects.get(date__range=week.vote_date_range,
                                      track=self)
        except Block.DoesNotExist:
            block = None

        self._block[week] = block

        return block

    def derived_title(self):
        return self.split_id3_title()[0]

    def derived_role(self):
        return self.split_id3_title()[1]

    def split_id3_title(self):
        try:
            return self.split_id3_title_cache
        except AttributeError:
            pass

        self.split_id3_title_cache = split_id3_title(self.id3_title)
        return self.split_id3_title_cache

    def artist(self):
        return self.id3_artist

    def canonical_string(self):
        """ Get the string that, for instance, would be tweeted """
        title, role = split_id3_title(self.id3_title)
        if role:
            return u'‘%s’ (%s) - %s' % (title, role, self.id3_artist)
        else:
            return u'‘%s’ - %s' % (title, self.id3_artist)

    def deets(self):
        return ('%s: %s - %s - %s - %i msec - %s'
                % (self.id, self.id3_title, self.id3_artist, self.id3_album,
                   self.msec, self.added))

    def current_week(self, time=None):
        try:
            week = self._current_week
        except AttributeError:
            week = Week(time)
            self._current_week = week
        return week

    def eligible(self, time=None):
        """ Returns True if self can be requested at time """
        if self.ineligible():
            return False
        else:
            return True

    def ineligible(self, time=None):
        """
        Returns a string describing why a track is ineligible, or False if it
        is not
        """

        try:
            return self.reason
        except AttributeError:
            pass

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

    def vote_week(self, time=None):
        """ Get whatever week we should be using to inspect votes """
        try:
            week = self._vote_week
        except AttributeError:
            week = Week(time)
            self._vote_week = week
        return week

    def votes(self, time=None):
        try:
            return self.vote_cache
        except AttributeError:
            pass

        week = self.vote_week(time)
        self.vote_cache = week._votes(track=self)

        return self.vote_cache

    def manual_votes(self, time=None):
        try:
            return self.manual_vote_cache
        except AttributeError:
            pass

        week = self.vote_week(time)
        self.manual_vote_cache = week._manual_votes(track=self)
        return self.manual_vote_cache

    def has_votes(self):
        """ Return True if Track has Votes or ManualVotes """
        return self.votes() or self.manual_votes()

    def shortlist(self, time=None):
        time = now_or_time(time)
        week = self.current_week(time)
        return week.shortlist(self)

    def discard(self, time=None):
        time = now_or_time(time)
        week = self.current_week(time)
        return week.discard(self)

    def slug(self):
        return slugify(self.derived_title())

    def rel_url(self):
        return '/%s/%s/' % (self.slug(), self.id)

    def url(self):
        return 'http://nkd.su' + self.rel_url()

    def vote_url(self):
        tweet = '@%s %s' % (settings.READING_USERNAME, self.url())
        url = 'https://twitter.com/intent/tweet?text=%s' % urlquote(tweet)
        return url

    def set_week(self, week):
        """
        Make this track get the votes (but not eligibility or anything else)
        from a particular week.
        """

        self._vote_week = week

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


class Vote(models.Model):
    def __unicode__(self):
        try:
            return '%s for %s at %s; "%s"' % (self.screen_name,
                                              self.tracks.all()[0],
                                              self.date, self.content())
        except IndexError:
            return '%s at %s: "%s"' % (self.screen_name, self.date,
                                       self.content())

    screen_name = models.CharField(max_length=100)
    text = models.CharField(max_length=140)
    user_id = models.IntegerField()
    tweet_id = models.IntegerField(primary_key=True)
    track = models.ForeignKey(Track, blank=True, null=True)  # deprecated
    tracks = models.ManyToManyField(Track, blank=True, related_name='multi+')
    date = models.DateTimeField()
    user_image = models.URLField()
    name = models.CharField(max_length=20)

    def derive_tracks_from_url_list(self, url_list):
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
        try:
            return self.content_cache
        except AttributeError:
            pass

        content = self.text.replace('@%s' %
                                    settings.READING_USERNAME, '').strip('- ')
        for word in content.split():
            if re.match('https?://[^\s]+', word):
                content = content.replace(word, '').strip()
            elif len(word) == 16 and re.match('[0-9A-F]{16}', word):
                # for the sake of old pre-url votes
                content = content.replace(word, '').strip()

        self.content_cache = content
        return self.content_cache

    def relevant_prior_voted_tracks(self):
        """
        Return a list of tracks that this vote's issuer has already voted for
        this Week
        """

        # every vote placed after the cutoff for this track by this person
        prior_votes = Week(self.date)._votes(track=self.track).filter(
            user_id=self.user_id)
        # all tracks requested by this person
        prior_tracks = set()
        for vote in prior_votes:
            for track in vote.tracks.all():
                prior_tracks.add(track)

        return prior_tracks

    def clean(self):
        if not self.tracks:
            raise ValidationError('no tracks in vote')

    def get_tracks(self):
        try:
            return self.tracks_cache
        except AttributeError:
            pass
        self.tracks_cache = self.tracks.all()
        return self.tracks_cache

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

    def when(self):
        """
        Return a human-readable representation of when this vote was placed.
        """

        return when(self.date)

    def week(self):
        return Week(self.date)

    def twitter_url(self):
        return 'http://twitter.com/%s/status/%s/' % (self.screen_name,
                                                     self.tweet_id)

    def user_url(self):
        return reverse('user', kwargs={'screen_name': self.screen_name})


class Play(models.Model):
    def __str__(self):
        return '<played %s at %s>' % (self.track, self.datetime)

    datetime = models.DateTimeField()
    track = models.ForeignKey(Track)
    tweet_id = models.IntegerField(blank=True)

    def clean(self):
        if (not is_on_air(self.datetime)) and (not settings.DEBUG):
            # let me tweet whenever if i'm in debug mode, jesus
            raise ValidationError('It is not currently showtime.')

        for play in Play.objects.filter(track=self.track):
            if play.datetime.date() == self.datetime.date():
                raise ValidationError('This has been played today already.')

        self.track.hidden = False
        self.track.save()

    def week(self):
        return Week(self.datetime)


KINDS = (
    ('email', 'email'),
    ('text', 'text'),
    ('tweet', 'tweet'),
)


class Block(models.Model):
    track = models.ForeignKey(Track)
    reason = models.CharField(max_length=256)
    date = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.track.ineligible():
            raise ValidationError('track is already blocked')


class Shortlist(models.Model):
    date = models.DateTimeField(auto_now_add=True)
    track = models.ForeignKey(Track)

    def clean(self):
        conflict = Week(self.date).shortlist_or_discard(self.track)
        if conflict:
            conflict.delete()


class Discard(models.Model):
    date = models.DateTimeField(auto_now_add=True)
    track = models.ForeignKey(Track)

    def clean(self):
        conflict = Week(self.date).shortlist_or_discard(self.track)
        if conflict:
            conflict.delete()


class ManualVote(models.Model):
    track = models.ForeignKey(Track, editable=False)
    kind = models.CharField(max_length=10, choices=KINDS)
    name = models.CharField(max_length=100, blank=True)
    message = models.CharField(max_length=256, blank=True)
    anonymous = models.BooleanField()
    date = models.DateTimeField(auto_now_add=True)

    def get_tracks(self):
        """ For vague compatability with Vote """
        try:
            return self.tracks_cache
        except AttributeError:
            pass
        self.tracks_cache = [self.track]
        return self.tracks_cache


class RobotApocalypse(models.Model):
    """ We have no control over the show this week. Many apologies. """
    overridden_showdate = models.DateField(unique=True)

    def clean(self):
        if self.overridden_showdate.weekday() != Week.showtime_day:
            raise ValidationError(
                "I'm not convinced there would normally be a show on that day")


class ScheduleOverride(models.Model):
    """ The show will be at a different time this week. """
    overridden_showdate = models.DateField(unique=True)
    start = models.DateTimeField()
    finish = models.DateTimeField()

    def clean(self):
        if self.overridden_showdate.weekday() != Week.showtime_day:
            raise ValidationError(
                "I'm not convinced there would normally be a show on that day")

        if self.start > self.finish:
            raise ValidationError(
                "The start time should not be after the end time")


class Request(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    successful = models.BooleanField()
    blob = models.TextField()

    def serialise(self, struct):
        self.blob = json.dumps(struct)

    def struct(self):
        return json.loads(self.blob)

    def when(self):
        return when(self.created)
