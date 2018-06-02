from django.conf import settings
from django.conf.urls import patterns, include, url
from django.contrib import admin

from nkdsu.apps.vote import urls as vote_urls

admin.autodiscover()

urlpatterns = patterns(
    '',
    url(r'^', include(vote_urls, namespace='vote')),
    url(r'^admin/', include(admin.site.urls)),

    # registration
    url(r'^logout/', 'django.contrib.auth.views.logout', {'next_page': '/'},
        name='logout'),
    url(r'^login/', 'django.contrib.auth.views.login', name='login'),
    url(r'^cpw/', 'django.contrib.auth.views.password_change',
        name='password_change'),
    url(r'^cpw-done/', 'django.contrib.auth.views.password_change_done',
        name='password_change_done'),
)

if settings.DEBUG:
    urlpatterns += patterns(
        '',
        (r'^media/(?P<path>.*)$', 'django.views.static.serve', {
            'document_root': settings.MEDIA_ROOT}))
