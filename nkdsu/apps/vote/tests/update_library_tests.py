from django.test import TestCase

from ..models import Track
from ..update_library import metadata_consistency_checks


class MetadataConsistencyCheckTest(TestCase):
    def test_anime_and_role_required_if_inudesu_false(self):
        self.assertEqual(
            metadata_consistency_checks(Track(id3_title='No role at all'), [], []),
            [
                {'field': 'anime', 'message': 'field is missing'},
                {'field': 'role', 'message': 'field is missing'},
            ],
        )
