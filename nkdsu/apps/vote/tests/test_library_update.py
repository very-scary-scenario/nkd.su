import plistlib
from collections import namedtuple
from typing import Any, Iterable, Optional

from django.test import TestCase

from ..models import Track
from ..update_library import metadata_consistency_checks, update_library


SINGLE_TRACK_XML = '''
    <key>{key}</key>
    <dict>
        <key>Track ID</key><integer>{key}</integer>
        <key>Name</key><string>{name}</string>
        <key>Artist</key><string>{artist}</string>
        {album_xml}
        <key>Kind</key><string>MPEG audio file</string>
        <key>Composer</key><string>{composer}</string>
        <key>Year</key><integer>{year}</integer>
        <key>Total Time</key><integer>{time}</integer>
        <key>Date Added</key><date>{added}</date>
        <key>Persistent ID</key><string>{hex_id}</string>
    </dict>
'''

PLIST_TEMPLATE = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple Computer//DTD PLIST 1.0//EN"
"http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Major Version</key><integer>1</integer>
    <key>Minor Version</key><integer>1</integer>
    <key>Date</key><date>2020-01-10T23:31:52Z</date>
    <key>Library Persistent ID</key><string>E30ACFF4167B0422</string>
    <key>Tracks</key>
    <dict>
{tracks}
    </dict>
</dict>
</plist>
'''

TrackMeta = namedtuple(
    'TrackMeta',
    ('key', 'name', 'artist', 'album', 'composer', 'year', 'time', 'added', 'hex_id'),
)

DEFAULT_TRACKS = [
    TrackMeta(
        "1",
        "Canpeki Shinakya! (Ro-Kyu-Bu! Character Song: Saki)",
        "Hikasa Youko",
        "Ro-Kyu-Bu! Character Songs 03 - Nagatsuka Saki|Lucky Star ED4",
        "idk, someone",
        "2014",
        "225044",
        "2012-12-15T18:51:21Z",
        "0007C3F2760E0541",
    ),
    TrackMeta(
        "2",
        "Hajimete no iro (The World God Only Knows EP4 Insert)",
        "Sakurai Tomo",
        "Kami Nomi zo Shury Sekai Character CD. - Asuka Sora",
        "someone else",
        "2013",
        "216894",
        "2010-12-03T17:24:49Z",
        "001D8E8B3A5DDDB9",
    ),
    TrackMeta(
        "3",
        "Runrunriru Ranranrara (Maria Holic Alive OP)",
        "Kobayashi Yuu",
        "Maria Holic Alive OP and ED Album - Runrunriru Ranranrara",
        "person",
        "2014",
        "238393",
        "2011-05-25T13:24:48Z",
        "0028E1FE6D1141B7",
    ),
    TrackMeta(
        "4",
        "Neguse (Tamako Market ED)",
        "Suzaki Aya",
        "Tamako Market ED Single - Neguse",
        "folks",
        "1973",
        "232907",
        "2013-01-26T12:39:37Z",
        "00340A1B035648A9",
    ),
    TrackMeta(
        "5",
        'Hands Around My Throat (Animatrix "Beyond" Insert)',
        "Death in Vegas",
        "The Animatrix - The Album (OST)",
        "folks",
        "1972",
        "305893",
        "2011-03-19T19:12:21Z",
        "00555AF6AC71CB70",
    ),
    TrackMeta(
        "6",
        "Day Game (Angel Beats Character Song: Girls Dead Monster)",
        "Girls Dead Monster (LiSA Singing)",
        "Ichiban no Takaramono ~Yui final ver.~",
        "",
        "1971",
        "293146",
        "2010-12-05T12:55:06Z",
        "00590FF313BD5557",
    ),
    TrackMeta(
        "7",
        "ft. (Fairy Tail OP3)",
        "FUNKIST",
        "Fairy Tail OP ED Theme Songs Vol.1",
        "",
        "1971",
        "211905",
        "2012-11-16T00:05:05Z",
        "00D12BB6D5ED72A7",
    ),
    TrackMeta(
        "8",
        "CAT'S EYE (Cat's Eye OP1|Gintama Insert Song EP84)",
        "Anri",
        "Cat's Eye",
        "",
        "1983",
        "195604",
        "2020-12-19T17:59:17Z",
        "89EE2CEBC58E2CAE",
    ),
]


class LibraryUpdateTest(TestCase):
    fixtures = ['vote.json']

    def get_track_xml(self, track: TrackMeta) -> str:
        album_xml_template = "<key>Album</key><string>{album}</string>"
        track_dict = track._asdict()
        if track.album:
            track_dict['album_xml'] = album_xml_template.format(album=track.album)
        else:
            track_dict['album_xml'] = ""

        return SINGLE_TRACK_XML.format(**track_dict)

    def get_library_xml(self, tracks: Iterable[TrackMeta]) -> bytes:
        return PLIST_TEMPLATE.format(
            tracks=[self.get_track_xml(track) for track in tracks]
        ).encode()

    def library_plus_one_track(
        self,
        name: str,
        artist: str,
        composer: str,
        year: str,
        time: str,
        added: str,
        hex_id: str,
        album: Optional[str] = None,
    ) -> dict[str, Any]:
        return plistlib.loads(
            self.get_library_xml(
                DEFAULT_TRACKS
                + [
                    TrackMeta(
                        len(DEFAULT_TRACKS) + 1,
                        name,
                        artist,
                        album,
                        composer,
                        year,
                        time,
                        added,
                        hex_id,
                    )
                ]
            )
        )

    def library_change_one_track(
        self, hex_id: str, new_meta: dict[str, str]
    ) -> dict[str, Any]:
        tracks = DEFAULT_TRACKS[:]
        for track_id, track in enumerate(tracks):
            if track.hex_id == hex_id:
                track_dict = track._asdict()
                for field in (
                    'name',
                    'artist',
                    'album',
                    'composer',
                    'time',
                    'added',
                    'year',
                ):
                    if field in new_meta:
                        track_dict[field] = new_meta[field]
                tracks[track_id] = TrackMeta(**track_dict)
        return plistlib.loads(self.get_library_xml(tracks))


class LibraryUpdateDryRunTest(LibraryUpdateTest):
    def test_new_track_matching_artist(self) -> None:
        tree = self.library_plus_one_track(
            "Koi Hana (Kaichou wa Maid-sama! Character Song)",
            "Hanazawa Kana and Kobayashi Yuu",
            "more people",
            "2021",
            "254000",
            "2010-09-02T02:00:00Z",
            "ADDD70C2D748ECC7",
        )
        results = update_library(tree, dry_run=True)
        self.assertEqual(len(results), 1, results)

        result = results[0]
        self.assertEqual(result['type'], 'new')
        self.assertEqual(
            result['item'],
            u"\u2018Koi Hana\u2019 (Kaichou wa Maid-sama! Character Song) "
            "- Hanazawa Kana and Kobayashi Yuu",
        )

    def test_new_track_non_matching_artist_and_anime(self) -> None:
        tree = self.library_plus_one_track(
            "Universal Bunny (Macross Frontier Movies Insert Song)",
            "Sheryl Nome starring May'n",
            "a giant robot",
            "2021",
            "357000",
            "2010-11-11T02:00:00Z",
            "0D096C693DA38F51",
        )
        results = update_library(tree, dry_run=True)
        self.assertEqual(len(results), 1, results)

        result = results[0]
        self.assertEqual(result['type'], 'new')
        self.assertEqual(
            result['item'],
            u"\u2018Universal Bunny\u2019 (Macross Frontier Movies Insert "
            "Song) - Sheryl Nome starring May'n",
        )

    def test_new_track_almost_matching_artist(self) -> None:
        tree = self.library_plus_one_track(
            "23:50 (Angel Beats Character Song - Girls Dead Monster)",
            "Girls Dead Monster (Lisa Singing)",
            "a moltres gijinka",
            "2021",
            "261000",
            "2010-06-28T02:00:00Z",
            "765682E348A46C30",
        )
        results = update_library(tree, dry_run=True)
        self.assertGreater(len(results), 1, results)
        warning_count = 0
        for result in results:
            warnings = result.get('warnings', None)
            if warnings:
                self.assertEqual(len(warnings), 1)
                warning_count += 1
                self.assertIn("LiSA Singing", warnings[0].get('message', ""))

        self.assertEqual(warning_count, 1)

    def test_new_track_artist_wrong_order(self) -> None:
        tree = self.library_plus_one_track(
            "Koi Hana (Kaichou wa Maid-sama! Character Song)",
            "Kana Hanazawa and Yuu Kobayashi",
            "a dragon",
            "2021",
            "254000",
            "2010-09-02T02:00:00Z",
            "ADDD70C2D748ECC7",
        )
        results = update_library(tree, dry_run=True)
        self.assertGreater(len(results), 1, results)
        warning_count = 0
        for result in results:
            warnings = result.get('warnings', None)
            if warnings:
                self.assertEqual(len(warnings), 1)
                warning_count += 1
                self.assertIn("Kobayashi Yuu", warnings[0].get('message', ""))

        self.assertEqual(warning_count, 1)

    def test_new_track_artist_almost_wrong_order(self) -> None:
        tree = self.library_plus_one_track(
            "Koi Hana (Kaichou wa Maid-sama! Character Song)",
            "Kana Hanazawa and Yui Kobayashi",
            "imagine dragons",
            "2021",
            "254000",
            "2010-09-02T02:00:00Z",
            "ADDD70C2D748ECC7",
        )
        results = update_library(tree, dry_run=True)
        self.assertGreater(len(results), 1, results)
        warning_count = 0
        for result in results:
            warnings = result.get('warnings', None)
            if warnings:
                self.assertEqual(len(warnings), 1)
                warning_count += 1
                self.assertIn("Kobayashi Yuu", warnings[0].get('message', ""))

        self.assertEqual(warning_count, 1)

    def test_new_track_matching_anime(self) -> None:
        tree = self.library_plus_one_track(
            "All 4 You (The World God Only Knows Insert Song EP5)",
            "Kanon Nakagawa (Touyama Nao)",
            "the friendly blobs from locoroco",
            "2021",
            "250000",
            "2011-03-07T02:00:00Z",
            "F2FDCB0308431FB4",
        )
        results = update_library(tree, dry_run=True)
        self.assertEqual(len(results), 1, results)

        result = results[0]
        self.assertEqual(result['type'], 'new')
        self.assertEqual(
            result['item'],
            u"\u2018All 4 You\u2019 (The World God Only Knows Insert Song "
            "EP5) - Kanon Nakagawa (Touyama Nao)",
        )

    def test_new_track_almost_matching_anime(self) -> None:
        tree = self.library_plus_one_track(
            "All 4 You (The world G-d Only Knows Insert Song EP5)",
            "Kanon Nakagawa (Touyama Nao)",
            "the protagonist of zoe mode's 'crush'",
            "2021",
            "250000",
            "2011-03-07T02:00:00Z",
            "F2FDCB0308431FB4",
        )
        results = update_library(tree, dry_run=True)
        self.assertGreater(len(results), 1, results)
        warning_count = 0
        for result in results:
            warnings = result.get('warnings', None)
            if warnings:
                self.assertEqual(len(warnings), 1)
                warning_count += 1
                self.assertIn(
                    "The World God Only Knows", warnings[0].get('message', "")
                )

        self.assertEqual(warning_count, 1)

    def test_new_track_almost_matching_artist_and_anime(self) -> None:
        tree = self.library_plus_one_track(
            "Dramatic Market Ride (Tamako makret OP)",
            "Suzako Aya",
            "sergei",
            "2021",
            "260000",
            "2013-01-26T02:00:00Z",
            "4ACC4F068C0E4C16",
        )
        results = update_library(tree, dry_run=True)
        self.assertGreater(len(results), 1, results)
        warning_count = 0
        for result in results:
            warnings = result.get('warnings', None)
            if warnings:
                warning_count += 1
                self.assertEqual(len(warnings), 2)
                fields = set()
                for warning in warnings:
                    field = warning.get('field', None)
                    fields.add(field)
                    if field == 'anime':
                        self.assertIn("Tamako Market", warning['message'])
                    elif field == 'artist':
                        self.assertIn("Suzaki Aya", warning['message'])
                    else:
                        self.fail("Unexpected warning field")
                self.assertEqual(fields, {'anime', 'artist'})

        self.assertEqual(warning_count, 1)

    def test_removing_track(self) -> None:
        tree = plistlib.loads(self.get_library_xml(DEFAULT_TRACKS[:-1]))
        results = update_library(tree, dry_run=True)

        self.assertEqual(len(results), 1, results)
        self.assertIn('type', results[0])
        self.assertEqual(results[0]['type'], 'hide')

    def test_new_track_has_parsing_error(self) -> None:
        tree = self.library_plus_one_track(
            "Born This Way (feat. YZERR, Vingo &amp; Bark) (Kengan Ashura ED)",
            "BAD HOP feat.YZERR,Vingo＆Bark",
            "popplio",
            "2021",
            "168000",
            "2011-03-07T02:00:00Z",
            "2A25990D66A020E6",
        )
        results = update_library(tree, dry_run=True)
        self.assertGreater(len(results), 1, results)
        warning_count = 0
        for result in results:
            warnings = result.get('warnings', None)
            if warnings:
                self.assertEqual(len(warnings), 1)
                warning_count += 1
                self.assertEqual(
                    warnings[0].get('message'),
                    "Illegal character ',' at index 18",
                )

        self.assertEqual(warning_count, 1)


class LibraryUpdateWetRunTest(LibraryUpdateTest):
    def test_add_track(self) -> None:
        tree = self.library_plus_one_track(
            "Koi Hana (Kaichou wa Maid-sama! Character Song)",
            "Hanazawa Kana and Kobayashi Yuu",
            "I.R.I.S.",
            "2021",
            "254000",
            "2010-09-02T02:00:00Z",
            "ADDD70C2D748ECC7",
        )
        update_library(tree, dry_run=False)
        try:
            db_track = Track.objects.get(id="ADDD70C2D748ECC7")
        except Track.DoesNotExist:
            self.fail("Track was not added to the database")

        self.assertEqual(db_track.artist, "Hanazawa Kana and Kobayashi Yuu")
        self.assertEqual(db_track.title, "Koi Hana")
        self.assertEqual(db_track.role, "Kaichou wa Maid-sama! Character Song")
        self.assertEqual(db_track.msec, 254000)

    def test_change_locked_track(self) -> None:
        hex_id = "00555AF6AC71CB70"
        Track.objects.filter(id=hex_id).update(metadata_locked=True)
        tree = self.library_change_one_track(hex_id, {'artist': "Death in Reno"})
        update_library(tree, dry_run=False)
        db_track = Track.objects.get(id=hex_id)
        self.assertEqual(db_track.artist, 'Death in Vegas')


class MetadataConsistencyCheckTest(TestCase):
    def test_anime_and_role_required_if_inudesu_false(self) -> None:
        self.assertEqual(
            metadata_consistency_checks(
                Track(id3_title='Complete role (Some kind of anime)'), [], [], []
            ),
            [],
        )

        self.assertEqual(
            metadata_consistency_checks(Track(id3_title='No role at all'), [], [], []),
            [
                {'field': 'anime', 'message': 'field is missing'},
                {'field': 'role', 'message': 'field is missing'},
            ],
        )

        self.assertEqual(
            metadata_consistency_checks(
                Track(id3_title='no role, but who cares', inudesu=True), [], [], []
            ),
            [],
        )

    def test_slight_artist_mismatch(self) -> None:
        self.assertEqual(
            metadata_consistency_checks(
                Track(
                    id3_title='title (role)',
                    id3_artist='an artist of some kind',
                ),
                [],
                [
                    'an artist of some kind',
                ],
                [],
            ),
            [],
        )

        self.assertEqual(
            metadata_consistency_checks(
                Track(
                    id3_title='title (role)',
                    id3_artist='an artist of some knid',
                ),
                [],
                [
                    'an artist of some kind',
                ],
                [],
            ),
            [
                {
                    'field': 'artist',
                    'message': (
                        '"an artist of some knid" was not found in the database, but it'
                        ' looks similar to "an artist of some kind"'
                    ),
                }
            ],
        )

        self.assertEqual(
            metadata_consistency_checks(
                Track(
                    id3_title='title (role)',
                    id3_artist='a completely different artist',
                ),
                [],
                [
                    'an artist of some kind',
                ],
                [],
            ),
            [],
        )

        # the artist name but with the words reversed is a special case that we also handle:
        self.assertEqual(
            metadata_consistency_checks(
                Track(
                    id3_title='title (role)',
                    id3_artist='kind some of artist an',
                ),
                [],
                [
                    'an artist of some kind',
                ],
                [],
            ),
            [
                {
                    'field': 'artist',
                    'message': (
                        '"kind some of artist an" was not found in the database, but it'
                        ' looks similar to "an artist of some kind"'
                    ),
                }
            ],
        )

    def test_multiple_artists(self) -> None:
        self.assertEqual(
            metadata_consistency_checks(
                Track(
                    id3_title='title (role)',
                    id3_artist='one artist, a character (CV: a VA)',
                ),
                [],
                [
                    'one artist',
                    'a character',
                    'a VA',
                ],
                [],
            ),
            [],
        )

        self.assertEqual(
            metadata_consistency_checks(
                Track(
                    id3_title='title (role)',
                    id3_artist='one artist, a character (CV: a VAN)',
                ),
                [],
                [
                    'one artist',
                    'a character',
                    'a VA',
                ],
                [],
            ),
            [
                {
                    'field': 'artist',
                    'message': (
                        '"a VAN" was not found in the database, but it looks similar to'
                        ' "a VA"'
                    ),
                },
            ],
        )

    def test_lexer_error(self) -> None:
        self.assertEqual(
            metadata_consistency_checks(
                Track(
                    id3_title='title (role)',
                    id3_artist='(()',
                ),
                [],
                ['(('],
                [],
            ),
            [
                # it should both complain about the syntax...
                {
                    'field': 'artist',
                    'message': "Illegal character '(' at index 0",
                },
                # ...and also treat the invalid artist name as one complete artist:
                {
                    'field': 'artist',
                    'message': (
                        '"(()" was not found in the database, but it looks similar to'
                        ' "(("'
                    ),
                },
            ],
        )

        self.assertEqual(
            metadata_consistency_checks(
                Track(id3_title='title (role)', id3_artist='artist', composer='(()'),
                [],
                [],
                ['(('],
            ),
            [
                # it should both complain about the syntax...
                {
                    'field': 'composer',
                    'message': "Illegal character '(' at index 0",
                },
                # ...and also treat the invalid artist name as one complete artist:
                {
                    'field': 'composer',
                    'message': (
                        '"(()" was not found in the database, but it looks similar to'
                        ' "(("'
                    ),
                },
            ],
        )
