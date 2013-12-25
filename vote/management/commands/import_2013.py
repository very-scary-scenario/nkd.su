from dateutil import parser as date_parser
import ujson

from django.core.management.base import BaseCommand
from django.utils import timezone

from vote.models import Show


class Command(BaseCommand):
    args = 'filename'
    help = 'import data from a dumpdata from the old site'

    def handle(self, filename, *args, **options):
        with open(filename) as the_file:
            data = ujson.load(the_file)

        Show.objects.all().delete()

        self.create_old_shows()

        def data_for_model(model_name):
            return filter(lambda m: m['model'] == model_name, data)

        self.import_scheduleoverrides(data_for_model('vote.scheduleoverride'))

    def create_old_shows(self):
        """
        Create the weeks between the first show on record and today.
        """

        point = timezone.datetime(2012, 8, 23,
                                  tzinfo=timezone.get_current_timezone())
        last = timezone.now()

        while point <= last:
            Show.at(point)
            point += timezone.timedelta(days=1)

    def import_scheduleoverrides(self, instances):
        for instance in instances:
            fields = instance['fields']
            overridden = timezone.make_aware(date_parser.parse(
                fields['overridden_showdate']), timezone.utc)

            relevant_show = Show.at(overridden)
            relevant_show.showtime = date_parser.parse(fields['start'])
            relevant_show.end = date_parser.parse(fields['finish'])
            relevant_show.save()
