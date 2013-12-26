from dateutil import parser as date_parser
import ujson

from django.core.management.base import BaseCommand
from django.utils import timezone

from vote.models import Show, Track


class Command(BaseCommand):
    args = 'filename'
    help = 'import data from a dumpdata from the old site'

    def handle(self, filename, *args, **options):
        with open(filename) as the_file:
            data = ujson.load(the_file)

        Show.objects.all().delete()

        for track in Track.objects.all():
            # sqlite refuses to do this all at once
            track.delete()

        self.create_old_shows()

        def data_for_model(model_name):
            return filter(lambda m: m['model'] == model_name, data)

        for instance in data_for_model('vote.scheduleoverride'):
            self.import_scheduleoverride(instance)

        for instance in data_for_model('vote.track'):
            self.import_track(instance)

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

    def import_scheduleoverride(self, instance):
        fields = instance['fields']
        overridden = timezone.make_aware(date_parser.parse(
            fields['overridden_showdate']), timezone.utc)

        relevant_show = Show.at(overridden)
        relevant_show.showtime = date_parser.parse(fields['start'])
        relevant_show.end = date_parser.parse(fields['finish'])
        relevant_show.save()

    def import_track(self, instance):
        fields = instance['fields']

        track = Track(
            pk=instance['pk'],
            id3_artist=fields['id3_artist'],
            id3_title=fields['id3_title'],
            id3_album=fields['id3_album'],
            msec=fields['msec'],
            added=date_parser.parse(fields['added']),

            revealed=date_parser.parse(fields['added']),
            hidden=fields['hidden'],
            inudesu=fields['inudesu'],
        )
        track.save()
