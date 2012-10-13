from django.db import models
from django.utils import timezone
from django.conf import settings
import datetime
import re
from django.core.exceptions import ValidationError

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

    def _round_down_to_hour(self, time):
        """ Rounds time down to the nearest hour """
        delta = datetime.timedelta(minutes=time.minute, seconds=time.second, microseconds=time.microsecond)
        return time - delta

    def is_on_air(self, time=None):
        """ Returns True if the time specified (or now) is during this week's broadcast """
        time = now_or_time(time)
        return (time >= self.showtime) and (time < self.finish)

    def next(self):
        return Week(self.finish)

    def prev(self):
        """ Returns the previous Week. See next(). """
        return Week(self.start - datetime.timedelta(seconds=1))

    def plays(self, track=None, invert=False):
        """ Returns all plays, in chronological order, from this Week's show as a QuerySet """
        if invert:
            order = '-datetime'
        else:
            order = 'datetime'

        plays = Play.objects.filter(datetime__range=[self.start, self.finish]).order_by(order)

        if track:
            plays.filter(track=track)

        return plays

    def votes(self, track=None):
        votes, manual_votes = self.votes_in_a_tuple(track=track)
        return list(votes) + list(manual_votes)

    def votes_in_a_tuple(self, track=None):
        """ Returns all Votes and ManualVotes from this week in a tuple of QuerySets
        if track is specified, filters by track """
        votes = self._votes(track)
        manual_votes = self._manual_votes(track)
        return (votes, manual_votes)

    def _manual_votes(self, track=None):
        manual_votes = ManualVote.objects.filter(date__range=[self.start, self.finish]).order_by('date')
        if track:
            manual_votes = manual_votes.filter(track=track)
        return manual_votes

    def _votes(self, track=None):
        votes = Vote.objects.filter(date__range=[self.start, self.finish]).order_by('date')
        if track:
            votes = votes.filter(track=track)
        return votes


def split_id3_title(id3_title):
    """ Split a Title (role) ID3 title up """
    try:
        role = re.findall('\(.*?\)', id3_title)[-1]
    except IndexError:
        role = None
        title = id3_title
    else:
        title = id3_title.replace(role, '').strip()
        role = role[1:-1] # strip brackets

    return title, role


class Track(models.Model):
    def __unicode__(self):
        return self.canonical_string()

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

    def last_played(self):
        try:
            return Play.objects.filter(track=self).order_by('-datetime')[0].datetime
        except IndexError:
            return None

    def undoable(self):
        return Play.objects.all().order_by('-datetime')[0].track == self

    def derived_title(self):
        return split_id3_title(self.id3_title)[0]

    def derived_role(self):
        return split_id3_title(self.id3_title)[1]

    def artist(self):
        return self.id3_artist

    def canonical_string(self):
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
        try:
            # if this Track instance has already been checked, just return what was returned before
            return self.reason
        except AttributeError:
            pass

        week = Week(time)

        if week.plays().filter(track=self):
            self.reason = 'played this week'

        elif week.prev().plays().filter(track=self):
            self.reason = 'played last week'

        else:
            self.reason = False

        return self.reason

    def votes(self, time=None):
        time = now_or_time(time)
        week = Week(time)
        return week.votes(track=self)

class Vote(models.Model):
    def __unicode__(self):
        return '%s for %s at %s; "%s"' % (self.screen_name, self.track, self.date, self.content())

    screen_name = models.CharField(max_length=100)
    text = models.CharField(max_length=140)
    user_id = models.IntegerField()
    tweet_id = models.IntegerField(primary_key=True)
    track = models.ForeignKey(Track)
    date = models.DateTimeField()
    user_image = models.URLField()
    name = models.CharField(max_length=20)

    def content(self):
        return self.text.replace(str(self.track.id), '').replace('@%s' % settings.READING_USERNAME, '').strip()

    def clean(self):
        if not self.track.eligible(self.date):
            raise ValidationError('This track has been played recently.')

        # every vote placed after the cutoff for this track by this person
        prior_votes = Week(self.date)._votes(track=self.track).filter(user_id=self.user_id)

        # we still need to ensure that at least one of these requests happened before the one we're dealing with; we could be digging here
        for vote in prior_votes:
            if vote.date < self.date:
                raise ValidationError('Already requested by this person.')


class Play(models.Model):
    datetime = models.DateTimeField()
    track = models.ForeignKey(Track)
    tweet_id = models.IntegerField(blank=True)

    def clean(self):
        # we need to refuse to create a play if a track has already been marked as played today and if the show is not on air
        if not is_on_air(self.datetime):
            raise ValidationError('It is not currently showtime.')

        for play in Play.objects.filter(track=self.track):
            if play.datetime.date() == self.datetime.date():
                raise ValidationError('This has been played today already.')

        if not self.track.eligible(self.datetime):
            raise ValidationError('This track was played last week.')

KINDS = (
        ('email', 'email'),
        ('text', 'text'),
        ('tweet', 'tweet'),
        )

class ManualVote(models.Model):
    track = models.ForeignKey(Track, editable=False)
    kind = models.CharField(max_length=10, choices=KINDS)
    name = models.CharField(max_length=100, blank=True)
    message = models.CharField(max_length=256, blank=True)
    anonymous = models.BooleanField()
    date = models.DateTimeField(auto_now_add=True)
