from dateutil import parser as date_parser
import ujson

from django.core.management.base import BaseCommand
from django.utils import timezone

from nkdsu.apps.vote.models import Show, Track, Play, Block, Vote, TwitterUser


class Command(BaseCommand):
    args = 'filename'
    help = 'import data from a dumpdata from the old site'

    def handle(self, filename, *args, **options):
        with open(filename) as the_file:
            data = ujson.load(the_file)

        for model in [Show, Track, Play, Block, Vote, TwitterUser]:
            for instance in model.objects.all():
                instance.delete()

        self.create_old_shows()

        def data_for_model(model_name):
            return filter(lambda m: m['model'] == model_name, data)

        for model, func in [
            ('vote.scheduleoverride', self.import_scheduleoverride),
            ('vote.track', self.import_track),
            ('vote.play', self.import_play),
            ('vote.vote', self.import_vote),
            ('vote.block', self.import_block),
        ]:
            for instance in data_for_model(model):
                func(instance)

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

            hidden=fields['hidden'],
            inudesu=fields['inudesu'],
        )

        if not fields['hidden']:
            track.revealed = date_parser.parse(fields['added'])

        track.save()

    def import_play(self, instance):
        fields = instance['fields']

        play = Play(
            pk=instance['pk'],
            track=Track.objects.get(pk=fields['track']),
            tweet_id=fields['tweet_id'],
            date=fields['datetime'],
        )

        play.save()

    def import_vote(self, instance):
        fields = instance['fields']
        this_vote_date = date_parser.parse(fields['date'])

        user_qs = TwitterUser.objects.filter(id=fields['user_id'])

        user_meta = {
            k: fields[k] for k in ['screen_name', 'user_image', 'name']
        }

        if user_qs.exists():
            user = user_qs.get()
            if user.updated < this_vote_date:
                for attr, value in user_meta.iteritems():
                    setattr(user, attr, value)
                user.updated = this_vote_date
                user.save()
        else:
            user = TwitterUser(
                id=fields['user_id'],
                updated=this_vote_date,
                **user_meta
            )
            user.save()

        track_pks = fields['tracks']
        if fields['track'] is not None:
            track_pks.append(fields['track'])

        tracks = []
        for track_pk in track_pks:
            tracks.append(Track.objects.get(pk=track_pk))

        if tracks:
            vote = Vote(
                date=this_vote_date,
                text=fields['text'],
                twitter_user=user,
                tweet_id=instance['pk']
            )

            vote.save()

            for track in tracks:
                vote.tracks.add(track)

            vote.save()

    def import_block(self, instance):
        fields = instance['fields']

        block = Block(
            track=Track.objects.get(pk=fields['track']),
            show=Show.at(date_parser.parse(fields['date'])),
            reason=fields['reason'],
        )

        block.save()
