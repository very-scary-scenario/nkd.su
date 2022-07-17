from django.conf import settings
from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.urls import include, path, re_path as url
from django.views.generic.base import RedirectView
from django.views.static import serve

from nkdsu.apps.vote import urls as vote_urls

admin.autodiscover()

urlpatterns = [
    url(r'^', include(vote_urls)),
    path('admin/', admin.site.urls),

    path('s/', include('social_django.urls', namespace='social')),

    # registration
    url(r'^logout/', LogoutView.as_view(), {'next_page': '/'}, name='logout'),
    url(r'^login/', LoginView.as_view(), name='login'),
    url(r'^cpw/', PasswordChangeView.as_view(), name='password_change'),
    url(r'^cpw-done/', RedirectView.as_view(url='/'),
        name='password_change_done'),

]

if settings.DEBUG:
    urlpatterns += [
        url(r'^media/(?P<path>.*)$', serve, {
            'document_root': settings.MEDIA_ROOT,
        }),
    ]

    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns += [
            url(r'^__debug__/', include(debug_toolbar.urls)),
        ]
