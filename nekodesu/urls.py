from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', 'vote.views.summary', name='summary'),
    #url(r'^everything/$', 'vote.views.everything', name='everything'),
    url(r'^artist/(?P<artist>.+)/$', 'vote.views.artist', name='artist'),
    url(r'^info/$', 'vote.views.info', name='info'),
    url(r'^roulette/$', 'vote.views.roulette', name='roulette'),
    url(r'^roulette/(?P<mode>unplayed)/$', 'vote.views.roulette', name='roulette'),
    url(r'^show/(?P<date>[\d-]+)/$', 'vote.views.show', name='show'),
    url(r'^show/$', 'vote.views.latest_show', name='latest_show'),
    url(r'^recent/$', 'vote.views.added'),
    url(r'^added/$', 'vote.views.added', name='added'),
    url(r'^added/(?P<date>[\d-]+)/$', 'vote.views.added', name='added'),
    url(r'^search/$', 'vote.views.search_redirect', name='search_redirect'),
    url(r'^search/(?P<query>[^/]+)/$', 'vote.views.search', name='search'),
    url(r'^search/(?P<query>[^/]+)/(?P<pageno>\d+)$', 'vote.views.search', name='search'),
    url(r'^upload/$', 'vote.views.upload_library', name='upload_library'),
    url(r'^request/$', 'vote.views.request_addition', name='request_addition'),
    url(r'^stats/$', 'vote.views.stats', name='stats'),
    url(r'^user/(?P<screen_name>[_0-9a-zA-Z]+)/$', 'vote.views.user', name='user'),

    # peter functions
    url(r'^played/(?P<track_id>.+)/$', 'vote.views.mark_as_played', name='mark_as_played'),
    url(r'^unplay/(?P<track_id>.+)/$', 'vote.views.unmark_as_played', name='unmark_as_played'),

    url(r'^vote/(?P<track_id>.+)/$', 'vote.views.make_vote', name='make_vote'),

    url(r'^block/(?P<track_id>.+)/$', 'vote.views.make_block', name='make_block'),
    url(r'^unblock/(?P<track_id>.+)/$', 'vote.views.unblock', name='unblock'),

    url(r'^hidden/$', 'vote.views.hidden', name='hidden'),
    url(r'^hide/(?P<track_id>.+)/$', 'vote.views.hide', name='hide'),
    url(r'^unhide/(?P<track_id>.+)/$', 'vote.views.unhide', name='unhide'),

    url(r'^inudesu/$', 'vote.views.inudesu', name='inudesu'),

    url(r'^trivia/$', 'vote.views.bad_trivia', name='bad_trivia'),

    url(r'^shortlist/(?P<track_id>.+)/$', 'vote.views.shortlist', name='shortlist'),
    url(r'^shortlist_order/$', 'vote.views.shortlist_order', name='shortlist_order'),
    url(r'^discard/(?P<track_id>.+)/$', 'vote.views.discard', name='discard'),
    url(r'^unshortlist_or_undiscard/(?P<track_id>.+)/$', 'vote.views.unshortlist_or_undiscard', name='unshortlist_or_undiscard'),

    url(r'^abuse/(?P<user_id>.+)/$', 'vote.views.toggle_abuse', name='toggle_abuse'),

    # tracks
    url(r'^(?P<track_id>[0-9A-F]{16})/$', 'vote.views.track', name='track'),
    url(r'^(?P<slug>[^/]*)/(?P<track_id>[0-9A-F]{16})/$', 'vote.views.track', name='track_by_slug'),
    url(r'^(?P<track_id>[0-9A-F]{16})/report/$', 'vote.views.report_bad_metadata', name='report'),

    # registration
    url(r'^logout/', 'django.contrib.auth.views.logout', {'next_page': '/'}, name='logout'),
    url(r'^login/', 'django.contrib.auth.views.login', name='login'),

    # API
    url(r'^info/api/$', 'vote.views.api_docs', name='api_docs'),

    url(r'^api/$', 'vote.api.week', name='api'),
    url(r'^api/week/(?P<date>[\d-]+)/$', 'vote.api.week', name='api_week'),
    url(r'^api/week/$', 'vote.api.last_week', name='api_last_week'),
    url(r'^api/track/(?P<track_id>[0-9A-F]{16})/$', 'vote.api.track', name='api_track'),
    url(r'^api/search/$', 'vote.api.search', name='api_search'),

    # javascript responses
    url(r'^do/select/$', 'vote.views.do_select', name='do_select'),
    url(r'^do/deselect/$', 'vote.views.do_deselect', name='do_deselect'),
    url(r'^do/selection/$', 'vote.views.do_selection', name='do_selection'),
    url(r'^do/clear_selection/$', 'vote.views.do_clear_selection', name='do_clear_selection'),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)
