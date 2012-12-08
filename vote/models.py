# -*- coding: utf-8 -*-

from django.db import models
from django.utils import timezone
from django.conf import settings
import datetime
import re
from django.core.exceptions import ValidationError
from django.utils.http import urlquote
from time import time as timer

def print_timing(name, t1, t2):
    print '%s took %0.3f ms' % (name, (t2-t1)*1000.0)

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
    return Week(now_or_time(time)).is_on_air(time)


class Week(object):
    """ A week. Cut off at the end of each broadcast """
    def __str__(self):
        return '<week of %s>' % (self.showtime.date())

    def __repr__(self):
        return str(self)

    showtime_day = 5 # saturday
    start_hour = 21
    end_hour = 23
    target_tuple = (end_hour, 0, 0, showtime_day)
    target_showtime_tuple = (start_hour, 0, 0, showtime_day)
    show_locale = timezone.get_current_timezone()
    
    def _approach(self, time, target_tuple, forwards):
        """ Approach a given time one hour at a time until the time matches the
        target_tuple in hours """

        one_hour = datetime.timedelta(hours=1)

        while time.astimezone(self.show_locale).timetuple()[3:7] != target_tuple:
            if forwards:
                time = time + one_hour
            else:
                time = time - one_hour
        return time

    def __init__(self, time=None, correct=True):
        """ Create the Week in which time (or now) resides.
        
        If correct is True, (which it is by default), we'll correct for
        overridden times by choosing the next or previous week"""

        time = now_or_time(time)

        one_hour = datetime.timedelta(hours=1)

        # set up default values
        start = self._round_down_to_hour(time)
        start = self._approach(start, self.target_tuple, False)
        finish = self._approach(start + one_hour, self.target_tuple, True)
        showtime = self._approach(finish - one_hour, self.target_showtime_tuple, False)
        
        # necessary to do now for self.prev() to work
        self._prev_week_default_showtime = self._approach(start, self.target_showtime_tuple, False)
        self._next_week_default_showtime = self._approach(finish, self.target_showtime_tuple, True)

        # is this week's start time to be overridden? (ie. was last week's shwotime modified)
        try: prev_override = ScheduleOverride.objects.get(overridden_showdate=self._prev_week_default_showtime)
        except ScheduleOverride.DoesNotExist:
            # nope
            pass
        else:
            # yep
            start = self.prev().finish

        # are this week's showtime and finish to be overridden?
        try: this_override = ScheduleOverride.objects.get(overridden_showdate=showtime.date())
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

        # do we actually fall into this range? if not, we should try again
        # we del self._prev because we set it when we realised the time had to be overridden
        if correct:
            if time > self.finish:
                del self._prev
                self = self.__init__(self._next_week_default_showtime, correct=False)
            elif time < self.start:
                del self._prev
                self = self.__init__(self._prev_week_default_showtime, correct=False)

    def __eq__(self, other):
        return self.showtime == other.showtime

    def __ne__(self, other):
        return not self == other

    def _round_down_to_hour(self, time):
        """ Rounds time down to the nearest hour """
        delta = datetime.timedelta(minutes=time.minute, seconds=time.second, microseconds=time.microsecond)
        return time - delta

    def is_on_air(self, time=None):
        """ Returns True if the time specified (or now) is during this week's broadcast """
        time = now_or_time(time)
        return (time >= self.showtime) and (time < self.finish)

    def next(self):
        try: return self._next
        except AttributeError: pass
        self._next = Week(self._next_week_default_showtime, correct=False)
        self._next._prev = self
        return self._next

    def prev(self):
        """ Returns the previous Week. See also: next(). """
        try: return self._prev
        except AttributeError: pass
        self._prev = Week(self._prev_week_default_showtime, correct=False)
        self._prev._next = self
        return self._prev

    def has_plays(self):
        """ True if this week has any plays  """
        return Play.objects.filter(datetime__range=self.date_range).exists()

    def plays(self, track=None, invert=False, select_related=False):
        """ Returns all plays, in chronological order, from this Week's show as a QuerySet.
        If track is specified, gets plays of that track """
        if invert: order = '-datetime'
        else: order = 'datetime'
        
        plays = Play.objects.filter(datetime__range=self.date_range).order_by(order)
        
        if track: plays = plays.filter(track=track)
        if select_related: plays = plays.select_related()
        
        return plays

    def _shortlist_or_discard(self, track, c):
        """ Does the actual work for shortlist() and discard()
        c is the class to use """
        if track:
            try:
                return c.objects.get(date__range=self.date_range, track=track)
            except c.DoesNotExist:
                return None
        else:
            tracks = [s.track for s in c.objects.filter(date__range=self.date_range)]
            # to prevent redundant Week creation
            [setattr(t, '_vote_week', self) for t in tracks]
            [setattr(t, '_current_week', self) for t in tracks]
            return tracks

    def shortlist(self, track=None):
        """ Return a list of shortlisted tracks
        if track is specified, return its Shortlist object for this week if present or None """
        return self._shortlist_or_discard(track, Shortlist)

    def discard(self, track=None):
        """ Like shortlist(), but for discards """
        return self._shortlist_or_discard(track, Discard)

    def shortlist_or_discard(self, track):
        """ Return a shortlist or discard if there are shortlists or discards on this track this week, otherwise return False """
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
        
        # we need the track dict to be persistent so that stuff that is cacheable stays cached
        
        [track_dict.__setitem__(t.id, t) for v in votes for t in v.get_tracks()]

        vote_dict = {}
        for vote in votes:
            for track in vote.get_tracks():
                # to prevent redundant Week creation
                track._vote_week = self
                track._current_week = self
                if track.id not in vote_dict:
                    vote_dict[track.id] = 1
                    track_dict[track.id].vote_cache = [vote] # we'll be examining this later, may as well force it in now
                else:
                    vote_dict[track.id] += 1
                    track_dict[track.id].vote_cache.append(vote) # see above

        return sorted(track_dict.values(), reverse=True, key=lambda t: vote_dict[t.id])

    def votes(self, track=None):
        """ Get all votes of any kind (for a particular track) from this week """
        votes, manual_votes = self.votes_in_a_tuple(track=track)
        #return list(votes) + list(votes) + list(votes) + list(votes) + list(votes) + list(manual_votes)
        return list(votes) + list(manual_votes)

    def votes_in_a_tuple(self, track=None):
        """ Returns all Votes and ManualVotes from this week in a tuple of QuerySets
        if track is specified, filters by track """
        try: return self.vote_tuple_cache
        except AttributeError: pass
        votes = self._votes(track)
        manual_votes = self._manual_votes(track)
        self.vote_tuple_cache = (votes, manual_votes)
        return self.vote_tuple_cache

    def _manual_votes(self, track=None):
        manual_votes = ManualVote.objects.filter(date__range=self.date_range).order_by('date')
        if track: manual_votes = manual_votes.filter(track=track)
        else: manual_votes.select_related()
        return manual_votes

    def _votes(self, track=None):
        votes = Vote.objects.filter(date__range=self.date_range).order_by('date')
        if track: votes = votes.filter(tracks=track)
        else: votes.select_related()
        return votes

    def added(self, show_hidden=False):
        """ Return a QuerySet of all (unhidden) tracks added to the library this week """
        tracks = Track.objects.filter(added__range=self.date_range)

        if not show_hidden:
            tracks = tracks.filter(hidden=False)

        return tracks

def vote_tweet(tracks):
    return '@%s %s' % (settings.READING_USERNAME, ' '.join([t.url() for t in tracks]))

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
        role = role[1:-1] # strip brackets
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
    role = models.CharField(max_length=100, blank=True) # OP, ED, char
    msec = models.IntegerField(blank=True, null=True)
    added = models.DateTimeField(blank=True, null=True)
    hidden = models.BooleanField()

    def is_new(self, time=None):
        return self.added > self.current_week(time).start and (not self.last_played())

    def length_str(self):
        return length_str(self.msec)

    def last_played(self):
        """ Get the datetime of this track's most recent play """
        try: return self.last_play().datetime
        except AttributeError: return None

    def last_played_showtime(self):
        current_week = self.current_week()
        last_played = self.last_played()
        while current_week.start > last_played:
            current_week = current_week.prev()
        return current_week.showtime

    def last_play(self):
        """ Get the datetime this track's most recent Play """
        try: return self.last_play_cache
        except AttributeError: pass

        try: last_play = Play.objects.filter(track=self).order_by('-datetime')[0]
        except IndexError: last_play = None

        self.last_play_cache = last_play
        return self.last_play_cache

    def weeks_since_play(self, time=None):
        """ Get the number of shows that have ended since this track's most recent Play """
        try: return self._weeks_since_play
        except AttributeError: pass
        
        time = now_or_time(time)
        this_week = self.current_week(time)
        last_play = self.last_play()
        if last_play == None:
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
        """ Right now, get True if this track is the source of the most recent Play. Criteria subject to change. """
        return Play.objects.all().order_by('-datetime')[0].track == self

    def block(self, week=None):
        """ Get any block from the week specified """
        week = self.current_week()

        try: return self._block[week]
        except AttributeError: self._block = {}
        except KeyError: pass

        try: block = Block.objects.get(date__range=week.date_range, track=self)
        except Block.DoesNotExist: block = None

        self._block[week] = block

        return block

    def derived_title(self):
        return self.split_id3_title()[0]

    def derived_role(self):
        return self.split_id3_title()[1]

    def split_id3_title(self):
        try: return self.split_id3_title_cache
        except AttributeError: pass
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
        return '%s: %s - %s - %s - %i msec - %s' % (self.id, self.id3_title, self.id3_artist, self.id3_album, self.msec, self.added)

    def current_week(self, time=None):
        try: week = self._current_week
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
        """ Returns a string describing why a track is ineligible, or False if it is not """
        # if this Track instance has already been checked, just return what was returned before
        try: return self.reason
        except AttributeError: pass
        
        week = self.current_week()
        
        if self.hidden:
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
        try: week = self._vote_week
        except AttributeError:
            week = Week(time)
            self._vote_week = week
        return week

    def votes(self, time=None):
        try: return self.vote_cache
        except AttributeError: pass

        week = self.vote_week(time)
        self.vote_cache = week._votes(track=self)
        return self.vote_cache

    def manual_votes(self, time=None):
        try: return self.manual_vote_cache
        except AttributeError: pass

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
    
    def url(self):
        return 'http://nkd.su/%s/' % self.id

    def vote_url(self):
        tweet = '@%s %s' % (settings.READING_USERNAME, self.url())
        url = 'https://twitter.com/intent/tweet?text=%s' % urlquote(tweet)
        return url

    def set_week(self, week):
        """ Make this track get the votes (but not eligibility or anything else) from a particular week. """
        self._vote_week = week

class Vote(models.Model):
    def __unicode__(self):
        try:
            return '%s for %s at %s; "%s"' % (self.screen_name, self.tracks.all()[0], self.date, self.content())
        except IndexError:
            return '%s at %s: "%s"' % (self.screen_name, self.date, self.content())
    
    screen_name = models.CharField(max_length=100)
    text = models.CharField(max_length=140)
    user_id = models.IntegerField()
    tweet_id = models.IntegerField(primary_key=True)
    track = models.ForeignKey(Track, blank=True, null=True) # deprecated
    tracks = models.ManyToManyField(Track, blank=True, related_name='multi+') # new, canonical
    date = models.DateTimeField()
    user_image = models.URLField()
    name = models.CharField(max_length=20)

    def derive_tracks_from_url_list(self, url_list):
        tracks = []
        for url in url_list:
            print url
            track_id = url.strip('/')[-16:]
            print track_id
            track = Track.objects.get(id=track_id)
            tracks.append(track)
            print 'added %s' % track

        return tracks

    def content(self):
        try: return self.content_cache
        except AttributeError: pass

        content = self.text.replace('@%s' % settings.READING_USERNAME, '').strip('- ')
        for word in content.split():
            if re.match('https?://[^\s]+', word):
                content = content.replace(word, '').strip()
            elif len(word) == 16 and re.match('[0-9A-F]{16}', word):
                # for the sake of old pre-url votes
                content = content.replace(word, '').strip()

        self.content_cache = content
        return self.content_cache
    
    def relevant_prior_voted_tracks(self):
        """ Return a list of tracks that this vote's issuer has already voted for this Week """
        # every vote placed after the cutoff for this track by this person
        prior_votes = Week(self.date)._votes(track=self.track).filter(user_id=self.user_id)
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
        try: return self.tracks_cache
        except AttributeError: pass
        self.tracks_cache = self.tracks.all()
        return self.tracks_cache


class Play(models.Model):
    def __str__(self):
        return '<played %s at %s>' % (self.track, self.datetime)

    datetime = models.DateTimeField()
    track = models.ForeignKey(Track)
    tweet_id = models.IntegerField(blank=True)

    def clean(self):
        # we need to refuse to create a play if a track has already been marked as played today and if the show is not on air
        if (not is_on_air(self.datetime)) and (not settings.DEBUG):
            # let me tweet whenever if i'm in debug mode, jesus
            raise ValidationError('It is not currently showtime.')

        for play in Play.objects.filter(track=self.track):
            if play.datetime.date() == self.datetime.date():
                raise ValidationError('This has been played today already.')

        self.track.hidden=False
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
        try: return self.tracks_cache
        except AttributeError: pass
        self.tracks_cache = [self.track]
        return self.tracks_cache

class ScheduleOverride(models.Model):
    overridden_showdate = models.DateField(unique=True)
    start = models.DateTimeField()
    finish = models.DateTimeField()

    def clean(self):
        if self.overridden_showdate.weekday() != Week.showtime_day:
            raise ValidationError("I'm not convinced there would normally be a show on that day")

        if self.start > self.finish:
            raise ValidationError("The start time should not be after the end time")
