from django.contrib.auth import get_user_model
from django.test import TestCase

from instant_coverage import InstantCoverageMixin, optional


class EverythingTest(
    optional.ExternalLinks,
    optional.ValidHTML5,
    optional.ValidJSON,
    InstantCoverageMixin,
    TestCase,
):
    fixtures = ['vote.json']

    covered_urls = [
        '/vote-admin/abuse/46162630/',
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
        '/vote-admin/remove-note/2/',
        '/vote-admin/hidden/',
        '/vote-admin/inudesu/',
        '/vote-admin/artless/',
        '/vote-admin/add-manual-vote/0007C3F2760E0541/',
        '/vote-admin/upload/',
        '/vote-admin/requests/',
        '/vote-admin/trivia/',
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
        '/request/',
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
        '/folks/u/what/',
        '/login/',
        '/cpw/',
        '/cpw-done/',
        # it's important that logout be last since we have a sublcass of this
        # test that logs in at the start, and we want it to stay logged in
        '/logout/',
    ]

    uncovered_urls = [
        # some urls that require stuff to be in the session
        '/folks/profile/',
        '/request/',
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
        '/set-dark-mode/',
        # would require me to put twitter credentials in the public settings
        # file
        '/twitter-avatar/46162630/',
        '/twitter-avatar/46162630/?size=original',
    ]

    uncovered_includes = [
        (r'^admin/',),
        (r'^s/',),
    ]

    instant_tracebacks = True

    def setUp(self) -> None:
        super().setUp()
        user = get_user_model()(
            username='what',
            is_staff=True,
            is_superuser=True,
        )
        user.set_password('what')
        user.save()

    def ensure_all_urls_resolve(self, urls):
        # linode has robot protection that makes automated testing of links to their site impossible, so:
        del urls['https://www.linode.com/legal-privacy/']

        return super().ensure_all_urls_resolve(urls)


class LoggedInEverythingTest(EverythingTest):
    covered_urls = [
        # some views require you to be logged in
        '/folks/profile/'
        '/request/?t=0007C3F2760E0541',
    ] + EverythingTest.covered_urls

    def setUp(self) -> None:
        super().setUp()
        self.assertTrue(self.client.login(username='what', password='what'))
