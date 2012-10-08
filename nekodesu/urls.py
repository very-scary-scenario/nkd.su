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
    url(r'^search$', 'vote.views.search', name='search'),

    # registration
    url(r'^logout/', 'django.contrib.auth.views.logout', {'next_page': '/'}),
    url(r'^login/', 'django.contrib.auth.views.login'),

    # peter functions
    url(r'^played/(?P<track_id>.+)/$', 'vote.views.mark_as_played', name='mark_as_played'),
    url(r'^unplay/(?P<track_id>.+)/$', 'vote.views.unmark_as_played', name='unmark_as_played'),
    url(r'^vote/(?P<track_id>.+)/$', 'vote.views.make_vote', name='make_vote'),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)
