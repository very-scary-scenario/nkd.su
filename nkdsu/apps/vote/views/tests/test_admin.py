from bs4 import BeautifulSoup
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


class PostAboutPlayTest(VoteAdminViewTest):
    def test_track_strings_truncated_appropriately(self) -> None:
        track = Track.objects.create(
            id='123',
            id3_title='a' * 500,
            id3_artist='a' * 2000,
            added='2025-01-01T00:00:00Z',
            hidden=True,
            inudesu=False,
        )
        self.assertEqual(len(str(track)), 2505)

        resp = self.client.get(reverse('vote:admin:post_about_play', kwargs={'pk': track.pk}))
        self.assertEqual(resp.status_code, 200, resp.content)
        soup = BeautifulSoup(resp.content)
        post_about_play, = soup.select('dl.post-about-play')
        dts = post_about_play.select('dt')
        dds = post_about_play.select('dd input')

        self.assertEqual([
            (dt.text, len(dd['value']))
            for dt, dd in zip(dts, dds)
        ], [
            ('Twitter:', 279),  # ellipsis gets counted different
            ('Bluesky:', 300),
            ('Discord:', 2000),
        ])
