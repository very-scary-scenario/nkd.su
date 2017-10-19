from django.contrib.auth import get_user_model
from django.test import TestCase

from instant_coverage import InstantCoverageMixin, optional


class EverythingTest(
    optional.ExternalLinks, optional.ValidHTML5, optional.ValidJSON,
    InstantCoverageMixin, TestCase
):
    fixtures = ['vote.json']

    covered_urls = [
        '/vote-admin/abuse/46162630/',
        '/vote-admin/block/0007C3F2760E0541/',
        '/vote-admin/block/0007C3F2760E0541/reason?reason=announced',
        '/vote-admin/unblock/0007C3F2760E0541/',
        '/vote-admin/hide/0007C3F2760E0541/',
        '/vote-admin/unhide/0007C3F2760E0541/',
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
        '/vote-admin/trivia/',
        '/vote-admin/all-the-anime/',
        '/vote-admin/play/0007C3F2760E0541/',

        '/js/deselect/',
        '/js/select/',
        '/js/selection/',
        '/js/clear_selection/',

        '/api/',
        '/api/week/',
        '/api/week/2014-02-05/',
        '/api/track/0007C3F2760E0541/',
        '/api/track/0007C3F2760E0541/',
        '/api/search/?q=Canpeki',
        '/api/user/EuricaeriS/',

        '/',
        '/info/',
        '/info/api/',
        '/request/',
        '/roulette/',
        '/roulette/indiscriminate/',
        '/roulette/hipster/',
        '/archive/',
        '/stats/',
        '/0007C3F2760E0541/',
        '/canpeki-shinakya/0007C3F2760E0541/',
        '/0007C3F2760E0541/report/',
        '/artist/Hikasa Youko/',
        '/anime/RO-KYU-BU%21/',
        '/show/2014-02-05/',
        '/show/',
        '/added/2014-02-05/',
        '/added/',
        '/search/?q=Canpeki',
        '/user/EuricaeriS/',

        '/login/',

        # it's important that logout be last since we have a sublcass of this
        # test that logs in at the start, and we want it to stay logged in
        '/logout/',
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

        # would require me to put twitter credentials in the public settings
        # file
        '/pic/46162630/',
        '/pic/46162630/?size=original',
    ]

    uncovered_includes = [
        ('^admin/',)
    ]

    # instant_tracebacks = True


class LoggedInEverythingTest(EverythingTest):
    def setUp(self):
        super(LoggedInEverythingTest, self).setUp()
        user = get_user_model()(
            username='what',
            is_staff=True,
            is_superuser=True,
        )
        user.set_password('what')
        user.save()
        self.assertTrue(self.client.login(username='what', password='what'))
