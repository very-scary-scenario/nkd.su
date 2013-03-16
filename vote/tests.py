import datetime
from random import choice

from django.utils import unittest, timezone
from django.utils.http import urlencode
from django.utils.timezone import now
from django.core.urlresolvers import reverse
from django.test.client import Client

from models import Track, Week, ScheduleOverride, Play


onesec = datetime.timedelta(seconds=1)


def make_tracks(the_time=None, save=False):
    if not the_time:
        the_time = now()

    tracks = []
    for i in xrange(0, 40):
        track = Track(
            id='89ABCDEF%08i' % i,
            id3_title="Test Song %i (a test song)" % i,
            id3_artist="Test Artist %i" % (i % 5),
            id3_album="Test Album %i" % (i % 7),
            msec=10000 + 100*i,
            added=the_time - datetime.timedelta(i),
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
            overridden_showdate=self.allnighter_date,
            start=start,
            finish=finish,
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


class ViewTests(unittest.TestCase):
    def setUp(self):
        tracks = make_tracks(save=True)

        # make a play from last week
        Play(datetime=Week().prev().showtime + onesec,
             track=choice(tracks),
             tweet_id=1
             ).save()

    def test_status_code(self):
        """
        Ensure that every page eventually redirects to something that returns
        with HTTP 200
        """

        c = Client()

        track_id = choice(Track.objects.all()).id

        urls = [
            reverse('summary'),
            reverse('artist', kwargs={'artist': 'Test Artist 1'}),
            reverse('info'),
            reverse('roulette'),
            reverse('latest_show'),
            reverse('added'),
            reverse('search_redirect') + '?' + urlencode(
                {'query': 'faiofjdioafd'}),
            reverse('search_redirect') + '?' + urlencode(
                {'query': 'Test'}),
            reverse('api_search') + '?' + urlencode({'q': 'faiofjdioafd'}),
            reverse('api_search') + '?' + urlencode({'q': 'Test'}),
            reverse('api_last_week'),
            reverse('upload_library'),
            reverse('request_addition'),
            reverse('stats'),
            reverse('api_docs'),
            reverse('track', kwargs={'track_id': track_id}),
            reverse('api_track', kwargs={'track_id': track_id}),
            # needs fixtures :<
            # reverse('user', kwargs={'screen_name': 'mftb'})
        ]

        for url in urls:
            response = c.get(url)
            status_code = response.status_code

            while status_code in (302, 301):
                url = response['Location']
                response = c.get(url)
                status_code = response.status_code

            if status_code != 200:
                raise self.failureException(
                    '%s returned %i' % (url, status_code))
