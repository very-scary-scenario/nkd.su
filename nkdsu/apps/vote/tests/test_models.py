from django.core.exceptions import ValidationError
from django.test import TestCase

from ..models import Show, Track


class ShowTest(TestCase):
    def test_showtime_date_constraint(self) -> None:
        Show.objects.create(showtime='2038-01-01T12:00:00Z', end='2038-01-01T14:00:00Z')

        with self.assertRaises(ValidationError) as e:
            Show.objects.create(
                showtime='2038-01-01T16:00:00Z', end='2038-01-01T18:00:00Z'
            )
        self.assertEqual(
            str(e.exception),
            str({'__all__': ['Constraint “unique_showtime_dates” is violated.']}),
        )

        Show.objects.create(showtime='2038-01-02T12:00:00Z', end='2038-01-02T14:00:00Z')


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
