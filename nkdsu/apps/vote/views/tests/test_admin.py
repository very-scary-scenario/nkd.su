from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from nkdsu.apps.vote.models import Track


User = get_user_model()


class VoteAdminViewTest(TestCase):
    def setUp(self) -> None:
        user = User.objects.create(username='user', is_staff=True)
        user.set_password('pass')
        user.save()

        self.assertTrue(self.client.login(username='user', password='pass'))


class BlockTest(VoteAdminViewTest):
    maxDiff = None
    fixtures = ['vote.json']

    def test_add_block(self) -> None:
        reason = 'blocking this track!!!'

        def track() -> Track:
            return Track.objects.get(pk='00555AF6AC71CB70')

        self.assertIsNone(track().ineligible())

        resp = self.client.post(
            reverse('vote:admin:block', kwargs={'pk': track().pk}),
            data={'reason': reason},
            follow=True,
        )
        self.assertEqual(resp.redirect_chain, [('/', 302)])
        self.assertEqual(
            [m.message for m in resp.context['messages']],
            ["'Hands Around My Throat' blocked"],
        )

        self.assertEqual(track().ineligible(), reason)
