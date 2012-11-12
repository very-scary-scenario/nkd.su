from django.utils import unittest, timezone
from models import *
import datetime

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
        """ Make sure that Week properly corrects if the defined time falls into an overlap
        
        Since we specified self.weeks[1] by asking for a time during the allnighter, we can just use that
        """
        week = Week(self.allnighter.finish - datetime.timedelta(seconds=1))
        self.assertEqual(week.showtime.date(), self.allnighter_date)
        self.assertLess(week.prev().showtime.date(), self.allnighter_date)
        self.assertGreater(week.next().showtime.date(), self.allnighter_date)

    def test_week_overlaps(self):
        print self.weeks
        self.assertEqual(self.weeks[0].finish, self.weeks[1].start)
        self.assertEqual(self.weeks[1].finish, self.weeks[2].start)
