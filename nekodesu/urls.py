from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    url(r'^$', 'vote.views.summary', name='summary'),
    url(r'^everything/$', 'vote.views.everything', name='everything'),
    url(r'^artist/(?P<artist>.+)/$', 'vote.views.artist', name='artist'),
    url(r'^info/$', 'vote.views.info', name='info'),
    url(r'^roulette/$', 'vote.views.roulette', name='roulette'),
    url(r'^show/(?P<showdate>.+)/$', 'vote.views.show', name='show'),
    url(r'^show/$', 'vote.views.latest_show', name='latest_show'),
    url(r'^search/$', 'vote.views.search_redirect', name='search_redirect'),
    url(r'^search/(?P<query>.+)/$', 'vote.views.search', name='search'),
    url(r'^upload/$', 'vote.views.upload_library', name='upload_library'),
    url(r'^request/$', 'vote.views.request_addition', name='request_addition'),

    # registration
    url(r'^logout/', 'django.contrib.auth.views.logout', {'next_page': '/'}),
    url(r'^login/', 'django.contrib.auth.views.login'),

    # peter functions
    url(r'^played/(?P<track_id>.+)/$', 'vote.views.mark_as_played', name='mark_as_played'),
    url(r'^unplay/(?P<track_id>.+)/$', 'vote.views.unmark_as_played', name='unmark_as_played'),
    url(r'^vote/(?P<track_id>.+)/$', 'vote.views.make_vote', name='make_vote'),
    url(r'^block/(?P<track_id>.+)/$', 'vote.views.make_block', name='make_block'),
    url(r'^unblock/(?P<track_id>.+)/$', 'vote.views.unblock', name='unblock'),
    url(r'^shortlist/(?P<track_id>.+)/$', 'vote.views.shortlist', name='shortlist'),
    url(r'^discard/(?P<track_id>.+)/$', 'vote.views.discard', name='discard'),
    url(r'^unshortlist_or_undiscard/(?P<track_id>.+)/$', 'vote.views.unshortlist_or_undiscard', name='unshortlist_or_undiscard'),

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
