from django.conf import settings
from django.urls import include, re_path as url, path
from django.contrib import admin
from django.contrib.auth.views import LogoutView, login, PasswordChangeView
from django.views.static import serve
from django.views.generic.base import RedirectView

from nkdsu.apps.vote import urls as vote_urls

admin.autodiscover()

urlpatterns = [
    url(r'^', include(vote_urls)),
    path('admin/', admin.site.urls),

    # registration
    url(r'^logout/', LogoutView.as_view(), {'next_page': '/'}, name='logout'),
    url(r'^login/', login, name='login'),
    url(r'^cpw/', PasswordChangeView.as_view(), name='password_change'),
    url(r'^cpw-done/', RedirectView.as_view(url='/'),
        name='password_change_done'),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [
        url(r'^media/(?P<path>.*)$', serve, {
            'document_root': settings.MEDIA_ROOT,
        }),
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ]
