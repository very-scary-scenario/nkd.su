from django.conf.urls import patterns, url, include

from nkdsu.apps.vote import views
from nkdsu.apps.vote.views import admin


admin_patterns = patterns(
    '',
    url(r'^upload/$', 'nkdsu.apps.vote.views.admin.upload_library', name='upload_library'),
    url(r'^play/(?P<pk>.+)/$', admin.Play.as_view(), name='play'),

    url(r'^add-manual-vote/(?P<pk>.+)/$',
        admin.ManualVote.as_view(), name='manual_vote'),

    url(r'^block/(?P<pk>[^/]+)/reason$',
        admin.MakeBlockWithReason.as_view(), name='block_with_reason'),
    url(r'^block/(?P<pk>[^/]+)/$',
        admin.MakeBlock.as_view(), name='block'),
    url(r'^unblock/(?P<pk>[^/]+)/$',
        admin.Unblock.as_view(), name='unblock'),

    url(r'^hidden/$', 'nkdsu.apps.vote.views.admin.hidden', name='hidden'),
    url(r'^hide/(?P<pk>.+)/$', admin.Hide.as_view(), name='hide'),
    url(r'^unhide/(?P<pk>.+)/$', admin.Unhide.as_view(), name='unhide'),

    url(r'^inudesu/$', 'nkdsu.apps.vote.views.admin.inudesu', name='inudesu'),

    url(r'^trivia/$', 'nkdsu.apps.vote.views.admin.bad_trivia', name='bad_trivia'),

    url(r'^shortlist/(?P<pk>.+)/$',
        admin.MakeShortlist.as_view(), name='shortlist'),
    url(r'^shortlist_order/$', 'nkdsu.apps.vote.views.admin.shortlist_order', name='shortlist_order'),
    url(r'^discard/(?P<pk>.+)/$', admin.MakeDiscard.as_view(), name='discard'),
    url(r'^unshortlist_or_undiscard/(?P<pk>.+)/$', 'nkdsu.apps.vote.views.admin.unshortlist_or_undiscard', name='unshortlist_or_undiscard'),

    url(r'^abuse/(?P<user_id>.+)/$', 'nkdsu.apps.vote.views.admin.toggle_abuse', name='toggle_abuse'),
)

urlpatterns = patterns(
    '',
    url(r'^vote-admin/', include(admin_patterns, namespace='admin')),

    url(r'^$', views.IndexView.as_view(), name='index'),

    url(r'^archive/$', views.Archive.as_view(), name='archive'),

    url(r'^show/(?P<date>[\d-]+)/$', views.ShowDetail.as_view(), name='show'),
    url(r'^show/$', views.ShowDetail.as_view(), name='show'),

    url(r'^added/(?P<date>[\d-]+)/$', views.Added.as_view(), name='added'),
    url(r'^added/$', views.Added.as_view(), name='added'),

    url(r'^roulette/(?P<mode>indiscriminate|hipster)/$',
        views.Roulette.as_view(), name='roulette'),
    url(r'^roulette/$', views.Roulette.as_view(), name='roulette'),

    url(r'^search/$', views.Search.as_view(), name='search'),

    url(r'^user/(?P<screen_name>[_0-9a-zA-Z]+)/$',
        views.TwitterUserDetail.as_view(), name='user'),

    url(r'^artist/(?P<artist>.+)/$', views.Artist.as_view(), name='artist'),

    url(r'^stats/$', views.Stats.as_view(), name='stats'),

    url(r'^info/$', views.Info.as_view(), name='info'),

    url(r'^request/$',
        views.RequestAddition.as_view(), name='request_addition'),

    # tracks
    url(r'^(?P<pk>[0-9A-F]{16})/$', views.TrackDetail.as_view(), name='track'),
    url(r'^(?P<slug>[^/]*)/(?P<pk>[0-9A-F]{16})/$',
        views.TrackDetail.as_view(), name='track'),
    url(r'^(?P<pk>[0-9A-F]{16})/report/$',
        views.ReportBadMetadata.as_view(), name='report'),

    # API
    url(r'^info/api/$', views.APIDocs.as_view(), name='api_docs'),

    url(r'^api/$', 'nkdsu.apps.vote.api.week', name='api'),
    url(r'^api/week/(?P<date>[\d-]+)/$', 'nkdsu.apps.vote.api.week', name='api_week'),
    url(r'^api/week/$', 'nkdsu.apps.vote.api.last_week', name='api_last_week'),
    url(r'^api/track/(?P<track_id>[0-9A-F]{16})/$', 'nkdsu.apps.vote.api.track', name='api_track'),
    url(r'^api/search/$', 'nkdsu.apps.vote.api.search', name='api_search'),

    # javascript responses
    # url(r'^do/select/$', 'nkdsu.apps.vote.views.do_select', name='do_select'),
    # url(r'^do/deselect/$', 'nkdsu.apps.vote.views.do_deselect', name='do_deselect'),
    # url(r'^do/selection/$', 'nkdsu.apps.vote.views.do_selection', name='do_selection'),
    # url(r'^do/clear_selection/$', 'nkdsu.apps.vote.views.do_clear_selection', name='do_clear_selection'),
)
