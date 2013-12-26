import datetime

from django.test import TestCase
from django.utils import timezone

from models import Show


class ShowTest(TestCase):
    """
    Tests for Show objects. Many of these depend on Neko Desu continuing to be
    broadcast at 11pm.
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
        self.assertLess(show_count, 54)

    def test_cannot_make_show_too_far_in_future(self):
        Show.at(timezone.now())
        too_far = timezone.now() + datetime.timedelta(seconds=1)
        self.assertRaises(NotImplementedError, lambda: Show.at(too_far))
