from collections import namedtuple
import plistlib

from django.test import TestCase

from ..models import Track
from ..update_library import update_library


SINGLE_TRACK_XML = '''
    <key>{key}</key>
    <dict>
        <key>Track ID</key><integer>{key}</integer>
        <key>Name</key><string>{name}</string>
        <key>Artist</key><string>{artist}</string>
        {album_xml}
        <key>Kind</key><string>MPEG audio file</string>
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
    'TrackMeta', ('key', 'name', 'artist', 'album', 'time', 'added', 'hex_id')
)

DEFAULT_TRACKS = [
    TrackMeta(
        "1",
        "Canpeki Shinakya! (RO-KYU-BU! Character Song: Saki)",
        "Hikasa Youko",
        "RO-KYU-BU! Character Songs 03 - Nagatsuka Saki",
        "225044",
        "2012-12-15T18:51:21Z",
        "0007C3F2760E0541"
    ),
    TrackMeta(
        "2",
        "Hajimete no iro (The World God Only Knows EP4 Insert)",
        "Sakurai Tomo",
        "Kami Nomi zo Shury Sekai Character CD. - Asuka Sora",
        "216894",
        "2010-12-03T17:24:49Z",
        "001D8E8B3A5DDDB9"
    ),
    TrackMeta(
        "3",
        "Runrunriru Ranranrara (Maria Holic Alive OP)",
        "Kobayashi Yuu",
        "Maria Holic Alive OP and ED Album - Runrunriru Ranranrara",
        "238393",
        "2011-05-25T13:24:48Z",
        "0028E1FE6D1141B7"
    ),
    TrackMeta(
        "4",
        "Neguse (Tamako Market ED)",
        "Suzaki Aya",
        "Tamako Market ED Single - Neguse",
        "232907",
        "2013-01-26T12:39:37Z",
        "00340A1B035648A9"
    ),
    TrackMeta(
        "5",
        'Hands Around My Throat (Animatrix "Beyond" Insert)',
        "Death in Vegas",
        "The Animatrix - The Album (OST)",
        "305893",
        "2011-03-19T19:12:21Z",
        "00555AF6AC71CB70"
    ),
    TrackMeta(
        "6",
        "Day Game (Angel Beats Character Song: Girls Dead Monster)",
        "Girls Dead Monster (LiSA Singing)",
        "Ichiban no Takaramono ~Yui final ver.~",
        "293146",
        "2010-12-05T12:55:06Z",
        "00590FF313BD5557"
    ),
    TrackMeta(
        "7",
        "ft. (Fairy Tail OP3)",
        "FUNKIST",
        "Fairy Tail OP ED Theme Songs Vol.1",
        "211905",
        "2012-11-16T00:05:05Z",
        "00D12BB6D5ED72A7"
    )
]


class LibraryUpdateTest(TestCase):
    fixtures = ['vote.json']

    def get_track_xml(self, track):
        album_xml_template = "<key>Album</key><string>{album}</string>"
        track_dict = track._asdict()
        if track.album:
            track_dict['album_xml'] = album_xml_template.format(
                album=track.album
            )
        else:
            track_dict['album_xml'] = ""

        return SINGLE_TRACK_XML.format(**track_dict)

    def get_library_xml(self, tracks):
        return PLIST_TEMPLATE.format(
            tracks=[self.get_track_xml(track) for track in tracks]
        )

    def library_plus_one_track(self, name, artist, time, added, hex_id,
                               album=None):
        return plistlib.readPlistFromString(
            self.get_library_xml(
                DEFAULT_TRACKS + [TrackMeta(
                    len(DEFAULT_TRACKS) + 1,
                    name,
                    artist,
                    album,
                    time,
                    added,
                    hex_id
                )]
            )
        )

    def library_change_one_track(self, hex_id, new_meta):
        tracks = DEFAULT_TRACKS[:]
        for track_id, track in enumerate(tracks):
            if track.hex_id == hex_id:
                track_dict = track._asdict()
                for field in ('name', 'artist', 'album', 'time', 'added'):
                    if field in new_meta:
                        track_dict[field] = new_meta[field]
                tracks[track_id] = TrackMeta(**track_dict)
        return plistlib.readPlistFromString(self.get_library_xml(tracks))


class LibraryUpdateDryRunTest(LibraryUpdateTest):
    def test_new_track_matching_artist(self):
        tree = self.library_plus_one_track(
            "Koi Hana (Kaichou wa Maid-sama! Character Song)",
            "Hanazawa Kana and Kobayashi Yuu",
            "254000",
            "2010-09-02T02:00:00Z",
            "ADDD70C2D748ECC7"
        )
        results = update_library(tree, dry_run=True)
        self.assertEqual(len(results), 1)

        result = results[0]
        self.assertEqual(result['type'], 'new')
        self.assertEqual(
            result['item'],
            u"\u2018Koi Hana\u2019 (Kaichou wa Maid-sama! Character Song) "
            "- Hanazawa Kana and Kobayashi Yuu"
        )

    def test_new_track_non_matching_artist_and_anime(self):
        tree = self.library_plus_one_track(
            "Universal Bunny (Macross Frontier Movies Insert Song)",
            "Sheryl Nome starring May'n",
            "357000",
            "2010-11-11T02:00:00Z",
            "0D096C693DA38F51"
        )
        results = update_library(tree, dry_run=True)
        self.assertEqual(len(results), 1)

        result = results[0]
        self.assertEqual(result['type'], 'new')
        self.assertEqual(
            result['item'],
            u"\u2018Universal Bunny\u2019 (Macross Frontier Movies Insert "
            "Song) - Sheryl Nome starring May'n"
        )

    def test_new_track_almost_matching_artist(self):
        tree = self.library_plus_one_track(
            "23:50 (Angel Beats Character Song - Girls Dead Monster)",
            "Girls Dead Monster (Lisa Singing)",
            "261000",
            "2010-06-28T02:00:00Z",
            "765682E348A46C30"
        )
        results = update_library(tree, dry_run=True)
        self.assertGreater(len(results), 1)
        warning_count = 0
        for result in results:
            warnings = result.get('warnings', None)
            if warnings:
                self.assertEqual(len(warnings), 1)
                warning_count += 1
                self.assertIn("Girls Dead Monster (LiSA Singing)",
                              warnings[0].get('message', ""))

        self.assertEqual(warning_count, 1)

    def test_new_track_artist_wrong_order(self):
        tree = self.library_plus_one_track(
            "Koi Hana (Kaichou wa Maid-sama! Character Song)",
            "Kana Hanazawa and Yuu Kobayashi",
            "254000",
            "2010-09-02T02:00:00Z",
            "ADDD70C2D748ECC7"
        )
        results = update_library(tree, dry_run=True)
        self.assertGreater(len(results), 1)
        warning_count = 0
        for result in results:
            warnings = result.get('warnings', None)
            if warnings:
                self.assertEqual(len(warnings), 1)
                warning_count += 1
                self.assertIn("Kobayashi Yuu", warnings[0].get('message', ""))

        self.assertEqual(warning_count, 1)

    def test_new_track_artist_almost_wrong_order(self):
        tree = self.library_plus_one_track(
            "Koi Hana (Kaichou wa Maid-sama! Character Song)",
            "Kana Hanazawa and Yui Kobayashi",
            "254000",
            "2010-09-02T02:00:00Z",
            "ADDD70C2D748ECC7"
        )
        results = update_library(tree, dry_run=True)
        self.assertGreater(len(results), 1)
        warning_count = 0
        for result in results:
            warnings = result.get('warnings', None)
            if warnings:
                self.assertEqual(len(warnings), 1)
                warning_count += 1
                self.assertIn("Kobayashi Yuu", warnings[0].get('message', ""))

        self.assertEqual(warning_count, 1)

    def test_new_track_matching_anime(self):
        tree = self.library_plus_one_track(
            "All 4 You (The World God Only Knows Insert Song EP5)",
            "Kanon Nakagawa (Touyama Nao)",
            "250000",
            "2011-03-07T02:00:00Z",
            "F2FDCB0308431FB4"
        )
        results = update_library(tree, dry_run=True)
        self.assertEqual(len(results), 1)

        result = results[0]
        self.assertEqual(result['type'], 'new')
        self.assertEqual(
            result['item'],
            u"\u2018All 4 You\u2019 (The World God Only Knows Insert Song "
            "EP5) - Kanon Nakagawa (Touyama Nao)"
        )

    def test_new_track_almost_matching_anime(self):
        tree = self.library_plus_one_track(
            "All 4 You (The world G-d Only Knows Insert Song EP5)",
            "Kanon Nakagawa (Touyama Nao)",
            "250000",
            "2011-03-07T02:00:00Z",
            "F2FDCB0308431FB4"
        )
        results = update_library(tree, dry_run=True)
        self.assertGreater(len(results), 1)
        warning_count = 0
        for result in results:
            warnings = result.get('warnings', None)
            if warnings:
                self.assertEqual(len(warnings), 1)
                warning_count += 1
                self.assertIn("The World God Only Knows",
                              warnings[0].get('message', ""))

        self.assertEqual(warning_count, 1)

    def test_new_track_almost_matching_artist_and_anime(self):
        tree = self.library_plus_one_track(
            "Dramatic Market Ride (Tamako makret OP)",
            "Suzako Aya",
            "260000",
            "2013-01-26T02:00:00Z",
            "4ACC4F068C0E4C16"
        )
        results = update_library(tree, dry_run=True)
        self.assertGreater(len(results), 1)
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
                        self.assertIn("Tamako Market", warning.get('message'))
                    elif field == 'artist':
                        self.assertIn("Suzaki Aya", warning.get('message'))
                    else:
                        self.fail("Unexpected warning field")
                self.assertEqual(fields, {'anime', 'artist'})

        self.assertEqual(warning_count, 1)

    def test_removing_track(self):
        tree = plistlib.readPlistFromString(
            self.get_library_xml(DEFAULT_TRACKS[:-1])
        )
        results = update_library(tree, dry_run=True)

        self.assertEqual(len(results), 1)
        self.assertIn('type', results[0])
        self.assertEqual(results[0]['type'], 'hide')


class LibraryUpdateWetRunTest(LibraryUpdateTest):
    def test_add_track(self):
        tree = self.library_plus_one_track(
            "Koi Hana (Kaichou wa Maid-sama! Character Song)",
            "Hanazawa Kana and Kobayashi Yuu",
            "254000",
            "2010-09-02T02:00:00Z",
            "ADDD70C2D748ECC7"
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
