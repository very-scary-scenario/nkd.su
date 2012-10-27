from django.db import models
from django.utils import timezone
from django.conf import settings
import datetime
import re
from django.core.exceptions import ValidationError
from django.utils.http import urlquote

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
        return '%s - %s via %s' % (self.start, self.finish, self.showtime)

    showtime_day = 5 # saturday
    start_hour = 21
    end_hour = 23
    target_tuple = (end_hour, 0, 0, showtime_day)
    target_showtime_tuple = (start_hour, 0, 0, showtime_day)
    show_locale = timezone.get_current_timezone()

    def __init__(self, time=None):
        """ Create the Week in which time (or now) resides """
        time = now_or_time(time)

        one_hour = datetime.timedelta(hours=1)

        start = self._round_down_to_hour(time)
        while start.astimezone(self.show_locale).timetuple()[3:7] != self.target_tuple:
            start = start - one_hour

        finish = start + one_hour
        while finish.astimezone(self.show_locale).timetuple()[3:7] != self.target_tuple:
            finish = finish + one_hour

        showtime = finish - one_hour
        while showtime.astimezone(self.show_locale).timetuple()[3:7] != self.target_showtime_tuple:
            showtime = showtime - one_hour

        self.start = start
        self.finish = finish
        self.showtime = showtime
        self.date_range = [self.start, self.finish]

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
        try: return self.next_week
        except AttributeError: pass
        self.next_week = Week(self.finish)
        return self.next_week

    def prev(self):
        """ Returns the previous Week. See next(). """
        try: return self.prev_week
        except AttributeError: pass
        self.prev_week = Week(self.start - datetime.timedelta(seconds=1))
        return self.prev_week

    def has_plays(self):
        """ True if this week has any plays  """
        return Play.objects.filter(datetime__range=self.date_range).exists()

    def plays(self, track=None, invert=False, select_related=True):
        """ Returns all plays, in chronological order, from this Week's show as a QuerySet """
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
            return [s.track for s in c.objects.filter(date__range=self.date_range)]

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
    return '@%s %s' % (settings.READING_USERNAME, ' '.join([t.id for t in tracks]))

def tweet_url(tweet):
    return 'https://twitter.com/intent/tweet?text=%s' % urlquote(tweet)

def vote_url(tracks):
    return tweet_url(vote_tweet(tracks))

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
        return self.id == other.id

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

    def __init__(self, *args, **kwargs):
        models.Model.__init__(self, *args, **kwargs)
        self.week = None

    def length_str(self):
        return length_str(self.msec)

    def last_played(self):
        """ Get the datetime of this track's most recent play """
        try: return self.last_play().datetime
        except AttributeError: return None

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
        time = now_or_time(time)
        this_week = Week(time)
        last_play = self.last_play()
        if last_play == None:
            return None

        # prevent infinite loops, just in case
        assert time > last_play.datetime

        week = last_play.week()
        weeks_ago = 0

        while this_week != week:
            week = week.next()
            weeks_ago += 1

        return weeks_ago

    def undoable(self):
        """ Right now, get True if this track is the source of the most recent Play. Criteria subject to change. """
        return Play.objects.all().order_by('-datetime')[0].track == self

    def block(self, week=None):
        """ Get any block from the week specified """
        if not week:
            week = self.week

        try: return self.block_cache[week]
        except AttributeError: self.block_cache = {}
        except KeyError: pass

        try: block = Block.objects.get(date__range=week.date_range, track=self)
        except Block.DoesNotExist: block = None

        self.block_cache[week] = block

        return block


    def derived_title(self):
        return split_id3_title(self.id3_title)[0]

    def derived_role(self):
        return split_id3_title(self.id3_title)[1]

    def artist(self):
        return self.id3_artist

    def canonical_string(self):
        """ Get the string that, for instance, would be tweeted """
        title, role = split_id3_title(self.id3_title)
        if role:
            return u'"%s" (%s) - %s' % (title, role, self.id3_artist)
        else:
            return u'"%s" - %s' % (title, self.id3_artist)

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

        week = Week(time)
        
        if self.hidden:
            self.reason = 'hidden'

        elif week.plays().filter(track=self):
            self.reason = 'played this week'

        elif week.prev().plays().filter(track=self):
            self.reason = 'played last week'

        elif self.block(week):
            self.reason = self.block(week).reason

        else:
            self.reason = False

        return self.reason

    def vote_week(self, time):
        """ Get whatever week we should be using to inspect votes """
        if self.week and (not time):
            week = self.week
        else:
            time = now_or_time(time)
            week = Week(time)

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
        week = Week(time)
        return week.shortlist(self)

    def discard(self, time=None):
        time = now_or_time(time)
        week = Week(time)
        return week.discard(self)

    def vote_url(self):
        tweet = '@%s %s' % (settings.READING_USERNAME, self.id)
        url = 'https://twitter.com/intent/tweet?text=%s' % urlquote(tweet)
        return url

    def set_week(self, week):
        """ Make this track get the votes (but not eligibility or anything else) from a particular week. """
        self.week = week

class Vote(models.Model):
    def __unicode__(self):
        return '%s for %s at %s; "%s"' % (self.screen_name, self.tracks.all()[0], self.date, self.content())

    screen_name = models.CharField(max_length=100)
    text = models.CharField(max_length=140)
    user_id = models.IntegerField()
    tweet_id = models.IntegerField(primary_key=True)
    track = models.ForeignKey(Track, blank=True, null=True) # deprecated
    tracks = models.ManyToManyField(Track, blank=True, related_name='multi+') # new, canonical
    date = models.DateTimeField()
    user_image = models.URLField()
    name = models.CharField(max_length=20)

    def content(self):
        try: return self.content_cache
        except AttributeError: pass

        content = self.text.replace('@%s' % settings.READING_USERNAME, '').strip()
        for word in content.split():
            if len(word) == 16 and self.tracks.filter(id=word).exists():
                content = content.replace(word, '').strip()
            if word in ['-']:
                content = content.replace(word, '').strip()
        self.content_cache = content
        return self.content_cache

    def clean(self):
        # every vote placed after the cutoff for this track by this person
        prior_votes = Week(self.date)._votes(track=self.track).filter(user_id=self.user_id)
        # all tracks requested by this person
        prior_tracks = set()
        for vote in prior_votes:
            for track in vote.tracks.all():
                prior_tracks.add(track)

        self.save()
        for word in self.text.split():
            try:
                track = Track.objects.get(id=word)
            except Track.DoesNotExist:
                pass
            else:
                if track.eligible(self.date) and track not in prior_tracks:
                    print track
                    self.tracks.add(track)
                else:
                    # raise ValidationError(track.ineligible())
                    # we can let this pass; we just won't count it
                    pass

        if not self.tracks:
            raise ValidationError('no tracks in vote')

    def get_tracks(self):
        try: return self.tracks_cache
        except AttributeError: pass
        self.tracks_cache = self.tracks.all()
        return self.tracks_cache


class Play(models.Model):
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

