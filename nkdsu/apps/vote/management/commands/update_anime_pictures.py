from django.core.management.base import BaseCommand, CommandParser

from ...anime import get_anime
from ...models import Track


class Command(BaseCommand):
    help = "Update art for all present anime."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            '--force-refresh',
            action='store_true',
            default=False,
            help="Force retrieval of all anime images, even if they're already here",
        )

    def handle(self, *, force_refresh: bool, **options) -> None:
        for anime_title in Track.all_anime_titles():
            anime_detail = get_anime(anime_title)
            if anime_detail is not None:
                anime_detail.cached_picture_url(force_refresh=force_refresh)
