from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path, re_path as url
from django.views.static import serve
import social_django.urls

from nkdsu.apps.vote import urls as vote_urls
from nkdsu.views import LoginView, RegisterView, SetPasswordView

admin.autodiscover()

urlpatterns = [
    url(r'^', include(vote_urls)),
    path('admin/', admin.site.urls),
    path('s/', include(social_django.urls, namespace='social')),
    # registration
    url(r'^register/', RegisterView.as_view(), name='register'),
    url(
        r'^logout/', auth_views.LogoutView.as_view(), {'next_page': '/'}, name='logout'
    ),
    url(r'^login/', LoginView.as_view(), name='login'),
    url(r'^set-password/', SetPasswordView.as_view(), name='password_set'),
    path(
        'change-password/',
        auth_views.PasswordChangeView.as_view(),
        name='password_change',
    ),
    path(
        'change-password/done/',
        auth_views.PasswordChangeDoneView.as_view(),
        name='password_change_done',
    ),
    path(
        'reset-password/', auth_views.PasswordResetView.as_view(), name='password_reset'
    ),
    path(
        'reset-password/done/',
        auth_views.PasswordResetDoneView.as_view(),
        name='password_reset_done',
    ),
    path(
        'reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(),
        name='password_reset_confirm',
    ),
    path(
        'reset/done/',
        auth_views.PasswordResetCompleteView.as_view(),
        name='password_reset_complete',
    ),
]

if settings.DEBUG:
    urlpatterns += [
        url(
            r'^media/(?P<path>.*)$',
            serve,
            {
                'document_root': settings.MEDIA_ROOT,
            },
        ),
    ]

    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns += [
            url(r'^__debug__/', include(debug_toolbar.urls)),
        ]
