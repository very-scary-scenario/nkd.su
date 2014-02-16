import plistlib

from django.core.management.base import BaseCommand

from nkdsu.apps.vote.models import Track


class Command(BaseCommand):
    args = 'filename'
    help = 'import a playlist from a timestamped iTunes playlist'

    def handle(self, filename, *args, **options):
        with open(filename) as plist_file:
            self.plist = plistlib.readPlist(plist_file)
            self.import_playlists()

    def import_playlists(self):
        for playlist in self.plist['Playlists']:
            self.import_playlist(playlist)

    def import_playlist(self, playlist):
        for play in playlist['Playlist Items']:
            plist_track = self.plist['Tracks'][str(play['Track ID'])]
            pk = plist_track['Persistent ID']

            try:
                track = Track.objects.get(pk=pk)
            except Track.DoesNotExist:
                print "could not find '{Name}' ({pk})".format(
                    pk=pk, **plist_track
                )
                continue

            print track
