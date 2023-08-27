from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase

from instant_coverage import InstantCoverageMixin, optional

from .apps.vote.elfs import ELFS_NAME, is_elf


User = get_user_model()


class EverythingTest(
    optional.ExternalLinks,
    optional.ValidHTML5,
    optional.ValidJSON,
    InstantCoverageMixin,
    TestCase,
):
    fixtures = ['vote.json']

    covered_urls = [
        '/vote-admin/tw-abuse/46162630/',
        '/vote-admin/local-abuse/45/',
        '/vote-admin/block/0007C3F2760E0541/',
        '/vote-admin/block/0007C3F2760E0541/reason?reason=announced',
        '/vote-admin/unblock/0007C3F2760E0541/',
        '/vote-admin/hide/0007C3F2760E0541/',
        '/vote-admin/unhide/0007C3F2760E0541/',
        '/vote-admin/lm/0007C3F2760E0541/',
        '/vote-admin/ulm/0007C3F2760E0541/',
        '/vote-admin/shortlist/0007C3F2760E0541/',
        '/vote-admin/discard/0007C3F2760E0541/',
        '/vote-admin/reset/0007C3F2760E0541/',
        '/vote-admin/make-note/0007C3F2760E0541/',
        '/vote-admin/post-about-play/0007C3F2760E0541/',
        '/vote-admin/remove-note/2/',
        '/vote-admin/hidden/',
        '/vote-admin/inudesu/',
        '/vote-admin/artless/',
        '/vote-admin/add-manual-vote/0007C3F2760E0541/',
        '/vote-admin/upload/',
        '/vote-admin/requests/',
        '/vote-admin/check-metadata/',
        '/vote-admin/play/0007C3F2760E0541/',
        '/js/deselect/',
        '/js/select/',
        '/js/selection/',
        '/js/clear_selection/',
        '/api/',
        '/api/week/',
        '/api/week/2014-02-05/',
        '/api/track/0007C3F2760E0541/',
        '/api/search/?q=Canpeki',
        '/api/user/EuricaeriS/',
        '/',
        '/browse/',
        '/anime/',
        '/artists/',
        '/years/',
        '/composers/',
        '/roles/',
        '/info/',
        '/info/api/',
        '/info/privacy/',
        '/info/tos/',
        '/profile/',
        '/request/',
        '/request/?t=0007C3F2760E0541',
        '/request-addition/',
        '/roulette/',
        '/roulette/hipster/',
        '/roulette/indiscriminate/',
        '/roulette/pro/',
        '/roulette/staple/',
        '/roulette/decade/',
        '/roulette/decade/1970/',
        '/roulette/short/1/',
        '/archive/',
        '/archive/2014/',
        '/stats/',
        '/0007C3F2760E0541/',
        '/canpeki-shinakya/0007C3F2760E0541/',
        '/0007C3F2760E0541/report/',
        '/artist/Hikasa Youko/',
        '/anime/RO-KYU-BU%21/',
        '/composer/folks/',
        '/year/2014/',
        '/show/2014-02-05/listen/',
        '/show/2014-02-05/',
        '/show/',
        '/added/2014-02-05/',
        '/added/',
        '/search/?q=Canpeki',
        '/user/EuricaeriS/',
        '/@what/',
        '/profile/email/',
        '/profile/',
        '/confirm-email/',
        '/confirm-email/abc/',
        '/request/',
        '/login/',
        '/account/login/',
        '/register/',
        '/account/register/',
        '/change-password/',
        '/change-password/done/',
        '/reset-password/',
        '/reset-password/done/',
        '/reset-password/key/abc-def/',
        '/reset-password/key/done/',
        # it's important that logout be last since we have a sublcass of this
        # test that logs in at the start, and we want it to stay logged in
        '/logout/',
        '/account/logout/',
    ]

    uncovered_urls = [
        # some urls that require stuff to be in the session
        '/vote-admin/upload/confirm/',
        '/vote-admin/shortlist-selection/',
        '/vote-admin/discard-selection/',
        '/vote-admin/hide-selection/',
        '/vote-admin/unhide-selection/',
        '/vote-admin/reset-shortlist-discard-selection/',
        # only accepts POST
        '/vote-admin/shortlist-order/',
        '/vote-admin/requests/fill/1/',
        '/vote-admin/requests/claim/1/',
        '/vote-admin/requests/shelf/1/',
        '/set-dark-mode/',
        # can only be accessed if you are logged in with an unusable password
        '/set-password/',
        # is intentionally broken
        '/vote-admin/throw-500/',
    ]

    uncovered_includes = [
        (r'^admin/',),
        (r'^s/',),
    ]

    instant_tracebacks = True

    def setUp(self) -> None:
        super().setUp()
        user = User(username='what')
        user.set_password('what')
        user.save()

    def ensure_all_urls_resolve(self, urls):
        # linode has robot protection that makes automated testing of links to their site impossible, so:
        del urls['https://www.linode.com/legal-privacy/']

        # the cat's website returns HTTP 429 when crawled in these tests
        del urls['https://thecat.radio']

        return super().ensure_all_urls_resolve(urls)


class LoggedInEverythingTest(EverythingTest):
    def setUp(self) -> None:
        super().setUp()
        self.assertTrue(self.client.login(username='what', password='what'))


class ElfEverythingTest(EverythingTest):
    def setUp(self) -> None:
        super().setUp()
        us = User.objects.get(username='what')
        self.assertFalse(is_elf(us))
        elfs, _ = Group.objects.get_or_create(name=ELFS_NAME)
        us.groups.add(elfs)
        us.save()
        self.assertTrue(is_elf(us))
        self.assertTrue(self.client.login(username='what', password='what'))


class StaffEverythingTest(EverythingTest):
    def setUp(self) -> None:
        super().setUp()
        us = User.objects.get(username='what')
        self.assertFalse(us.is_staff)
        us.is_staff = True
        us.save()
        self.assertTrue(self.client.login(username='what', password='what'))
