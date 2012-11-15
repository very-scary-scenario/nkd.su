from django.utils import unittest, timezone
from models import *
import datetime
from random import choice

def make_tracks(the_time=None, save=False):
    if not the_time:
        the_time = datetime.datetime.utcnow()

    tracks = []
    for i in xrange(0, 40):
        track = Track(
                id = '0123456789ABCDEF',
                id3_title = "Test Song %i (a test song)" % i,
                id3_artist = "Test Artist %i" % (i%5),
                id3_album = "Test Album %i" % (i%7),
                msec = 10000 + 100*i,
                added = the_time - datetime.timedelta(i),
                )

        track.clean()
        tracks.append(track)

        if save:
            track.save()

    return tracks

class WeekTest(unittest.TestCase):
    def setUp(self):
        self.allnighter_date = datetime.date(2012, 11, 17)

        locale = timezone.get_current_timezone()

        start = locale.localize(datetime.datetime(2012, 11, 17, 21))
        finish = locale.localize(datetime.datetime(2012, 11, 18, 8))

        self.allnighter = ScheduleOverride(
                overridden_showdate = self.allnighter_date,
                start = start,
                finish = finish,
                )

        self.allnighter.clean()
        self.allnighter.save()

        week = Week(self.allnighter.start)

        self.weeks = [week.prev(), week, week.next()]

        self.addCleanup(ScheduleOverride.objects.all().delete)
    
    def test_week_caching(self):
        """ Make sure weeks always return the same prev() and next() """
        weeks = self.weeks
        self.assertEqual(id(weeks[2].prev()), id(weeks[1]))
        self.assertEqual(id(weeks[0].next()), id(weeks[1]))

        # and make sure this test would fail if it was broken
        del weeks[0]._next
        del weeks[2]._prev
        self.assertNotEqual(id(weeks[2].prev()), id(weeks[1]))
        self.assertNotEqual(id(weeks[0].next()), id(weeks[1]))
    
    def test_week_correction(self):
        """ Make sure that Week properly corrects if the defined time falls
        into an overlap """
        week = Week(self.allnighter.finish - datetime.timedelta(seconds=1))
        self.assertEqual(week.showtime.date(), self.allnighter_date)
        self.assertLess(week.prev().showtime.date(), self.allnighter_date)
        self.assertGreater(week.next().showtime.date(), self.allnighter_date)

    def test_week_coincidence(self):
        self.assertEqual(self.weeks[0].finish, self.weeks[1].start)
        self.assertEqual(self.weeks[1].finish, self.weeks[2].start)

    def test_play_pooling(self):
        tracks = make_tracks()
        onesec = datetime.timedelta(seconds = 1)

        # build a dict of week: playlist
        plays = {
                week: [
                    Play(datetime=week.start + onesec, track=choice(tracks)),
                    Play(datetime=week.finish - onesec, track=choice(tracks)),
                    ]
                    for week in self.weeks
                }
        
        # and make sure all our Plays think they're in the right week
        for week in plays:
            for play in plays[week]:
                self.assertEqual(week, play.week())

        print plays
