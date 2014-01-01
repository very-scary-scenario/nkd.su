from django.conf.urls import patterns, include, url
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns(
    '',
    url(r'^', include('nkdsu.apps.vote.urls', namespace='vote')),
    url(r'^admin/', include(admin.site.urls)),

    # registration
    url(r'^logout/', 'django.contrib.auth.views.logout', {'next_page': '/'},
        name='logout'),
    url(r'^login/', 'django.contrib.auth.views.login', name='login'),
)
