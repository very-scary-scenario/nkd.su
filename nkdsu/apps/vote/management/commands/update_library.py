import plistlib
from django.core.management.base import BaseCommand

from ...update_library import update_library


class Command(BaseCommand):
    args = '<...>'
    help = 'manually update library from songlibrary.xml'

    def handle(self, *args, **options):
        plistfile = open('songlibrary.xml')
        plist = plistlib.readPlistFromString(plistfile.read())

        if 'commit' in args:
            dry_run = False
        else:
            dry_run = True
            print("Performing dry run; 'commit' to confirm")

        self.stdout.write(
            '\n'.join([
                track['item'] for track in update_library(plist, dry_run=dry_run)
            ])
            + '\n'
        )
        plistfile.close()
