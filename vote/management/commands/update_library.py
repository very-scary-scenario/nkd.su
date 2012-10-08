from django.core.management.base import BaseCommand, CommandError
from vote.models import Track
from vote.update_library import update_library
import plistlib

class Command(BaseCommand):
    args = '<...>'
    help = 'manually update library from songlibrary.xml'

    def handle(self, *args, **options):
        tree = plistlib.readPlist('songlibrary.xml')

        if 'commit' in args:
            dry_run = False
        else:
            dry_run = True
            print "Performing dry run; 'commit' to confirm"

        self.stdout.write('\n'.join(update_library(tree, dry_run=dry_run))+'\n')
