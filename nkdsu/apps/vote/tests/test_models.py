from django.test import TestCase

from ..models import Track


class TrackTest(TestCase):
    fixtures = ['vote.json']

    def test_tweet_only_contains_first_role(self) -> None:
        track_with_multiple_roles = Track.objects.get(id3_album="Cat's Eye")

        # make sure it does actually have multiple roles:
        self.assertEqual(
            track_with_multiple_roles.roles,
            ["Cat's Eye OP1", "Gintama Insert Song EP84"],
        )

        self.assertEqual(
            track_with_multiple_roles.play_tweet_content(),
            "Now playing on #usedoken: ‘CAT'S EYE’ (Cat's Eye OP1) - Anri",
        )
