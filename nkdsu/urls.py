from allauth.account import views as allauth_views
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path, re_path as url, reverse_lazy
from django.views.generic import RedirectView
from django.views.static import serve
import social_django.urls

from nkdsu.apps.vote import urls as vote_urls
from nkdsu.views import (
    EmailView,
    LoginView,
    PasswordResetView,
    RegisterView,
    SetPasswordView,
)

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
    path("reset-password/", PasswordResetView.as_view(), name="account_reset_password"),
    path(
        "reset-password/done/",
        allauth_views.password_reset_done,
        name="account_reset_password_done",
    ),
    url(
        r"^reset-password/key/(?P<uidb36>[0-9A-Za-z]+)-(?P<key>.+)/$",
        allauth_views.password_reset_from_key,
        name="account_reset_password_from_key",
    ),
    path(
        "reset-password/key/done/",
        allauth_views.password_reset_from_key_done,
        name="account_reset_password_from_key_done",
    ),
    path('profile/email/', EmailView.as_view(), name='account_email'),
    path(
        'confirm-email/',
        allauth_views.email_verification_sent,
        name='account_email_verification_sent',
    ),
    url(
        r'^confirm-email/(?P<key>[-:\w]+)/$',
        allauth_views.confirm_email,
        name='account_confirm_email',
    ),
    # account-related views that allauth expects:
    path(
        'account/register/',
        RedirectView.as_view(url=reverse_lazy('register')),
        name='account_signup',
    ),
    path(
        'account/logout/',
        RedirectView.as_view(url=reverse_lazy('logout')),
        name='account_logout',
    ),
    path(
        'account/login/',
        RedirectView.as_view(url=reverse_lazy('login')),
        name='account_login',
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
