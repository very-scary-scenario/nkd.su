from django.test import TestCase

from ..models import Track
from ..update_library import metadata_consistency_checks


class MetadataConsistencyCheckTest(TestCase):
    def test_anime_and_role_required_if_inudesu_false(self):
        self.assertEqual(
            metadata_consistency_checks(Track(id3_title='Complete role (Some kind of anime)'), [], []),
            [],
        )

        self.assertEqual(
            metadata_consistency_checks(Track(id3_title='No role at all'), [], []),
            [
                {'field': 'anime', 'message': 'field is missing'},
                {'field': 'role', 'message': 'field is missing'},
            ],
        )

        self.assertEqual(
            metadata_consistency_checks(Track(id3_title='no role, but who cares', inudesu=True), [], []),
            [],
        )

    def test_slight_artist_mismatch(self):
        self.assertEqual(
            metadata_consistency_checks(Track(
                id3_title='title (role)',
                id3_artist='an artist of some kind',
            ), [], [
                'an artist of some kind',
            ]),
            [],
        )

        self.assertEqual(
            metadata_consistency_checks(Track(
                id3_title='title (role)',
                id3_artist='an artist of some knid',
            ), [], [
                'an artist of some kind',
            ]),
            [{
                'field': 'artist',
                'message': (
                    '"an artist of some knid" was not found in the database, but it looks similar to '
                    '"an artist of some kind"'
                ),
            }],
        )

        self.assertEqual(
            metadata_consistency_checks(Track(
                id3_title='title (role)',
                id3_artist='a completely different artist',
            ), [], [
                'an artist of some kind',
            ]),
            [],
        )

        # the artist name but with the words reversed is a special case that we also handle:
        self.assertEqual(
            metadata_consistency_checks(Track(
                id3_title='title (role)',
                id3_artist='kind some of artist an',
            ), [], [
                'an artist of some kind',
            ]),
            [{
                'field': 'artist',
                'message': (
                    '"kind some of artist an" was not found in the database, but it looks similar to '
                    '"an artist of some kind"'
                ),
            }],
        )
