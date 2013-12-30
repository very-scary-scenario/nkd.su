from django.conf.urls import patterns, url

from nkdsu.apps.vote import views


urlpatterns = patterns(
    '',
    url(r'^$', views.IndexView.as_view(), name='index'),

    url(r'^archive/$', views.Archive.as_view(), name='archive'),

    url(r'^show/(?P<date>[\d-]+)$', views.ShowDetail.as_view(), name='show'),
    url(r'^show/$', views.ShowDetail.as_view(), name='show'),

    url(r'^added/(?P<date>[\d-]+)/$', views.Added.as_view(), name='added'),
    url(r'^added/$', views.Added.as_view(), name='added'),

    url(r'^roulette/(?P<mode>indiscriminate|hipster)/$',
        views.Roulette.as_view(), name='roulette'),
    url(r'^roulette/$', views.Roulette.as_view(), name='roulette'),

    url(r'^search/$', views.Search.as_view(), name='search'),

    #url(r'^everything/$', 'nkdsu.apps.vote.views.everything', name='everything'),
    url(r'^artist/(?P<artist>.+)/$', 'nkdsu.apps.vote.views.artist', name='artist'),
    url(r'^info/$', 'nkdsu.apps.vote.views.info', name='info'),
    url(r'^upload/$', 'nkdsu.apps.vote.views.upload_library', name='upload_library'),
    url(r'^request/$', 'nkdsu.apps.vote.views.request_addition', name='request_addition'),
    url(r'^stats/$', 'nkdsu.apps.vote.views.stats', name='stats'),
    url(r'^user/(?P<screen_name>[_0-9a-zA-Z]+)/$', 'nkdsu.apps.vote.views.user', name='user'),

    # peter functions
    url(r'^played/(?P<track_id>.+)/$', 'nkdsu.apps.vote.views.mark_as_played', name='mark_as_played'),
    url(r'^unplay/(?P<track_id>.+)/$', 'nkdsu.apps.vote.views.unmark_as_played', name='unmark_as_played'),

    url(r'^vote/(?P<track_id>.+)/$', 'nkdsu.apps.vote.views.make_vote', name='make_vote'),

    url(r'^block/(?P<track_id>[^/]+)/reason$', 'nkdsu.apps.vote.views.make_block_with_reason', name='make_block_with_reason'),
    url(r'^block/(?P<track_id>[^/]+)/$', 'nkdsu.apps.vote.views.make_block', name='make_block'),
    url(r'^unblock/(?P<track_id>[^/]+)/$', 'nkdsu.apps.vote.views.unblock', name='unblock'),

    url(r'^hidden/$', 'nkdsu.apps.vote.views.hidden', name='hidden'),
    url(r'^hide/(?P<track_id>.+)/$', 'nkdsu.apps.vote.views.hide', name='hide'),
    url(r'^unhide/(?P<track_id>.+)/$', 'nkdsu.apps.vote.views.unhide', name='unhide'),

    url(r'^inudesu/$', 'nkdsu.apps.vote.views.inudesu', name='inudesu'),

    url(r'^trivia/$', 'nkdsu.apps.vote.views.bad_trivia', name='bad_trivia'),

    url(r'^shortlist/(?P<track_id>.+)/$', 'nkdsu.apps.vote.views.shortlist', name='shortlist'),
    url(r'^shortlist_order/$', 'nkdsu.apps.vote.views.shortlist_order', name='shortlist_order'),
    url(r'^discard/(?P<track_id>.+)/$', 'nkdsu.apps.vote.views.discard', name='discard'),
    url(r'^unshortlist_or_undiscard/(?P<track_id>.+)/$', 'nkdsu.apps.vote.views.unshortlist_or_undiscard', name='unshortlist_or_undiscard'),

    url(r'^abuse/(?P<user_id>.+)/$', 'nkdsu.apps.vote.views.toggle_abuse', name='toggle_abuse'),

    # tracks
    url(r'^(?P<track_id>[0-9A-F]{16})/$', 'nkdsu.apps.vote.views.track', name='track'),
    url(r'^(?P<slug>[^/]*)/(?P<track_id>[0-9A-F]{16})/$', 'nkdsu.apps.vote.views.track', name='track_by_slug'),
    url(r'^(?P<track_id>[0-9A-F]{16})/report/$', 'nkdsu.apps.vote.views.report_bad_metadata', name='report'),

    # registration
    url(r'^logout/', 'django.contrib.auth.views.logout', {'next_page': '/'}, name='logout'),
    url(r'^login/', 'django.contrib.auth.views.login', name='login'),

    # API
    url(r'^info/api/$', 'nkdsu.apps.vote.views.api_docs', name='api_docs'),

    url(r'^api/$', 'nkdsu.apps.vote.api.week', name='api'),
    url(r'^api/week/(?P<date>[\d-]+)/$', 'nkdsu.apps.vote.api.week', name='api_week'),
    url(r'^api/week/$', 'nkdsu.apps.vote.api.last_week', name='api_last_week'),
    url(r'^api/track/(?P<track_id>[0-9A-F]{16})/$', 'nkdsu.apps.vote.api.track', name='api_track'),
    url(r'^api/search/$', 'nkdsu.apps.vote.api.search', name='api_search'),

    # javascript responses
    url(r'^do/select/$', 'nkdsu.apps.vote.views.do_select', name='do_select'),
    url(r'^do/deselect/$', 'nkdsu.apps.vote.views.do_deselect', name='do_deselect'),
    url(r'^do/selection/$', 'nkdsu.apps.vote.views.do_selection', name='do_selection'),
    url(r'^do/clear_selection/$', 'nkdsu.apps.vote.views.do_clear_selection', name='do_clear_selection'),
)
