from django.db import models
from django.utils import timezone
import datetime
import re

# when is neko desu?
start_time = datetime.time(21)
end_time = datetime.time(23)
weekday = 5 # saturday

def is_on_air():
    """ Returns True if the show is currently on air """
    now = datetime.datetime.now()
    if now.hour >= start_time.hour and now.hour < end_time.hour and now.weekday() == weekday:
        return True
    else:
        return False


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


def showtime(prev_cutoff=False):
    """ Get the next showtime (or the end of the previous show) """
    now = datetime.datetime.now()

    next_showdate = datetime.date(now.year, now.month, now.day)

    if now.time() > end_time and now.weekday() == weekday:
        next_showdate += datetime.timedelta(7)

    next_showtime = datetime.datetime.combine(next_showdate, start_time)

    while next_showtime.weekday() != weekday:
        next_showtime += datetime.timedelta(1)

    if prev_cutoff:
        return next_showtime - (datetime.timedelta(7, hours=start_time.hour - end_time.hour))
    else:
        return next_showtime


class Track(models.Model):
    def __unicode__(self):
        return self.canonical_string()

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

    def canonical_string(self):
        title, role = split_id3_title(self.id3_title)
        if role:
            return u'"%s" (%s) - %s' % (title, role, self.id3_artist)
        else:
            return u'"%s" - %s' % (title, self.id3_artist)

    def eligible(self):
        """ Returns True if the track can be requested """
        if (not self.last_played()) or timezone.make_naive(self.last_played(), timezone.utc) + datetime.timedelta(7) < showtime(prev_cutoff=True):
            return True
        else:
            return False


class Vote(models.Model):
    screen_name = models.CharField(max_length=100)
    text = models.CharField(max_length=140)
    user_id = models.IntegerField()
    tweet_id = models.IntegerField()
    track = models.ForeignKey(Track)
    date = models.DateTimeField()
    user_image = models.URLField()

    def content(self):
        return self.text.replace(str(self.track.id), '').replace('@nkdsu', '').strip()

class Play(models.Model):
    datetime = models.DateTimeField()
    track = models.ForeignKey(Track)
