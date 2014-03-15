import datetime

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from models import Show, Track, Play


def mkutc(*args, **kwargs):
    return timezone.make_aware(datetime.datetime(*args, **kwargs),
                               timezone.utc)


class ShowTest(TestCase):
    """
    Tests for Show objects. Many of these depend on Neko Desu continuing to be
    broadcast at 9-11pm.
    """

    def setUp(self):
        Show.objects.all().delete()

    def test_make_show(self, wipe=True):
        # this may seem overly thorough, but it has already found bugs that
        # would otherwise have been missed:
        for hours in xrange(366*24, 0, -1):
            if wipe:
                Show.objects.all().delete()

            starter = (
                timezone.now().replace(tzinfo=timezone.get_current_timezone())
                -
                datetime.timedelta(hours=hours)
            )

            show = Show.at(starter)
            showtime = show.showtime.astimezone(
                timezone.get_current_timezone())
            self.assertEqual(showtime.hour, 21)
            self.assertEqual(showtime.minute, 0)
            self.assertEqual(showtime.second, 0)
            self.assertEqual(showtime.microsecond, 0)
            self.assertEqual(showtime.weekday(), 5)

            self.assertEqual(show.end - show.showtime,
                             datetime.timedelta(hours=2))

            self.assertGreater(show.end, starter)

    def test_get_show(self):
        self.test_make_show(wipe=False)
        show_count = Show.objects.all().count()
        self.assertGreater(show_count, 51)
        self.assertLess(show_count, 55)

    def test_get_show_far_in_future(self):
        make_current = lambda t: timezone.make_aware(
            t, timezone.get_current_timezone())

        for x in xrange(2):
            # these functions do different things depending on if shows already
            # exist, but there should be no visible difference between the
            # results of these different things
            ours = Show.at(make_current(datetime.datetime(3000, 1, 1)))
            self.assertEqual(Show.objects.all().count(), 1)
            self.assertEqual(ours.end.date(), datetime.date(3000, 1, 4))

        for x in xrange(2):
            ours = Show.at(make_current(datetime.datetime(3010, 1, 1)))
            self.assertEqual(Show.objects.all().count(), 523)
            self.assertEqual(ours.end.date(), datetime.date(3010, 1, 6))

    def test_cannot_make_overlapping_shows(self):
        Show(showtime=mkutc(2010, 1, 1),
             end=mkutc(2011, 1, 1)).save()

        for showtime, end, should_raise in [
            (mkutc(2009, 1, 1), mkutc(2010, 6, 1), True),
            (mkutc(2010, 6, 1), mkutc(2012, 1, 1), True),
            (mkutc(2010, 3, 1), mkutc(2010, 9, 1), True),
            (mkutc(2012, 1, 1), mkutc(2012, 2, 1), False),
            (mkutc(2009, 1, 1), mkutc(2009, 9, 1), False),
            # also, since we're here, make sure we can't make shows that end
            # before they begin
            (mkutc(2010, 1, 1), mkutc(2009, 1, 1), True),
        ]:
            def func():
                show = Show(showtime=showtime, end=end)
                show.save()
                show.delete()

            if should_raise:
                self.assertRaises(ValidationError, func)
            else:
                func()

    def test_calling_next_or_prev_on_only_show_returns_none(self):
        self.assertIs(None, Show.current().next())
        self.assertIs(None, Show.current().prev())


class PlayTest(TestCase):
    fixtures = ['vote.json']

    def setUp(self):
        Play.objects.all().delete()

    def test_plays_for_already_played_tracks_can_not_be_added(self):
        track_1, track_2 = Track.objects.all()[:2]
        track_1.play(tweet=False)
        track_2.play(tweet=False)

        self.assertEqual(Play.objects.all().count(), 2)
        self.assertRaises(ValidationError, lambda: track_2.play(tweet=False))
        self.assertEqual(Play.objects.all().count(), 2)

    def test_plays_can_be_edited_after_the_fact(self):
        play = Track.objects.all()[0].play(tweet=False)
        play.date = mkutc(2009, 1, 1)
        play.save()
