from django.db import models
from django.utils import timezone
import datetime
import re
from django.core.exceptions import ValidationError

# when is neko desu?
hour = 21
length = 2
weekday = 5 # saturday

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


def is_on_air(time=None):
    """ Returns True if the show is currently on air """
    if showtime(current=True, time=time):
        return True
    else:
        return False


def showtime(prev_start=False, prev_end=False, current=False, time=None, end=False):
    """ Get the next showtime (or the start or end of the previous show, or the start of the show currently airing or next end time) 
    prev_start gets the end of the show before the one we're currently taking requests for
    prev_end gets the end of the same show
    current returns the start time of the current show if one is airing right now, otherwise returns None
    end adds <length of show> to any resultant time
    time specifies a time to consider as now. if unspecified, now is literally now"""
    if time:
        now = time
    else:
        now = datetime.datetime.utcnow().replace(tzinfo=timezone.utc)

    local_tz = timezone.get_current_timezone()
    # we use today's date so we can get DST right... hopefully
    # that should only ever change when DST rolls over, but because it will ever change it must be checked every time
    local_start_time = local_tz.localize(datetime.datetime.combine(now.date(), datetime.time(hour)))
    start_time = timezone.utc.normalize(local_start_time.astimezone(timezone.utc))
    end_time = start_time + datetime.timedelta(hours=length)

    start_time = start_time.time()
    end_time = end_time.time()

    next_showdate = datetime.date(now.year, now.month, now.day)

    if now.time() > start_time and now.weekday() == weekday:
        # a show has started airing today
        if current and now.time() < end_time:
            # a show is airing and we care
            return datetime.datetime.combine(next_showdate, start_time)
        elif current:
            # we're too late and we care
            return None
        elif (end or prev_end or prev_start) and now.time() < end_time:
            # we're not too late because we're concerned with ends
            pass
        else:
            # the show starts next week
            next_showdate += datetime.timedelta(7)
    elif current:
        # also too early
        return None

    next_showtime = timezone.make_aware(datetime.datetime.combine(next_showdate, start_time), timezone.utc)

    while next_showtime.weekday() != weekday:
        next_showtime += datetime.timedelta(1)

    if prev_end:
        return next_showtime - (datetime.timedelta(7, hours=-length))
    elif prev_start:
        return next_showtime - (datetime.timedelta(7))
    elif end:
        return next_showtime + (datetime.timedelta(hours=length))
    else:
        return next_showtime


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

    def canonical_string(self):
        title, role = split_id3_title(self.id3_title)
        if role:
            return u'"%s" (%s) - %s' % (title, role, self.id3_artist)
        else:
            return u'"%s" - %s' % (title, self.id3_artist)

    def eligible(self, time=None):
        """ Returns True if the track can be requested """
        if time:
            now = time
        else:
            now = datetime.datetime.utcnow().replace(tzinfo=timezone.utc)

        if Play.objects.filter(track=self, datetime__lt=showtime(time=now, end=True), datetime__gt=showtime(time=now, prev_start=True)):
            return False
        else:
            return True

class Vote(models.Model):
    def __unicode__(self):
        return '%s for %s at %s; "%s"' % (self.screen_name, self.track, self.date, self.content())

    screen_name = models.CharField(max_length=100)
    text = models.CharField(max_length=140)
    user_id = models.IntegerField()
    tweet_id = models.IntegerField()
    track = models.ForeignKey(Track)
    date = models.DateTimeField()
    user_image = models.URLField()

    def content(self):
        return self.text.replace(str(self.track.id), '').replace('@nkdsu', '').strip()

    def clean(self):
        if not self.track.eligible(self.date):
            raise ValidationError('This track has been played recently.')

        # every vote placed after the cutoff for this track by this person
        prior_votes = Vote.objects.filter(user_id=self.user_id, track=self.track, date__gt=showtime(time=self.date, prev_end=True))

        # we still need to ensure that at least one of these requests happened before the one we're dealing with; we could be digging here
        for vote in prior_votes:
            if vote.date < self.date:
                raise ValidationError('Already requested by this person.')


class Play(models.Model):
    datetime = models.DateTimeField()
    track = models.ForeignKey(Track)

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
