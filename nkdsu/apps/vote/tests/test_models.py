from django.test import TestCase

from ..models import Play, Show, Track


class PlayTest(TestCase):
    fixtures = ['vote.json']

    def test_tweet_only_contains_first_role(self) -> None:
        track_with_multiple_roles = Track.objects.get(id3_album="Cat's Eye")

        # make sure it does actually have multiple roles:
        self.assertEqual(track_with_multiple_roles.roles, ["Cat's Eye OP1", "Gintama Insert Song EP84"])

        play = Play.objects.create(track=track_with_multiple_roles, date=Show.objects.all()[0].showtime)
        self.assertEqual(play.get_tweet_text(), "Now playing on #usedoken: ‘CAT'S EYE’ (Cat's Eye OP1) - Anri")
