from typing import Any
from urllib.parse import parse_qs, urlparse

from allauth.account import views as allauth_views
from django.contrib import messages
from django.contrib.auth import get_user_model, views as auth_views
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import CreateView, FormView

from .apps.vote.mixins import BreadcrumbMixin
from .apps.vote.models import Track
from .apps.vote.views.profiles import UpdateProfileView
from .forms import RegistrationForm, ResetPasswordForm
from .mixins import MarkdownView


User = get_user_model()


class LoginView(MarkdownView, auth_views.LoginView):
    template_name = auth_views.LoginView.template_name
    title = 'login'
    filename = 'TWITTER.md'

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)

        tracks = []

        query_string = urlparse(context[self.redirect_field_name]).query
        query = parse_qs(query_string)

        if query is not None:
            tracks = [
                get_object_or_404(Track, pk=pk)
                for pk_string in query.get('t', [])
                for pk in pk_string.split(',')
            ]

        return {
            **context,
            'is_vote': bool(tracks),  # this is naive, but we don't use ?t= for a lot
            'registration_form': RegistrationForm(),
        }


class RegisterView(CreateView):
    template_name = 'auth/register.html'
    model = User
    form_class = RegistrationForm
    success_url = reverse_lazy('vote:profiles:edit-profile')

    def form_valid(self, form: RegistrationForm) -> HttpResponse:
        resp = super().form_valid(form)
        messages.success(
            self.request, 'Registration complete! Log in to edit your profile.'
        )
        return resp


class SetPasswordView(FormView):
    template_name = 'auth/set_password.html'
    form_class = SetPasswordForm
    success_url = reverse_lazy('login')

    def get_form_kwargs(self) -> dict[str, Any]:
        return {**super().get_form_kwargs(), 'user': self.request.user}

    @classmethod
    def as_view(cls, **kw):
        return user_passes_test(
            lambda u: u.is_authenticated and not u.has_usable_password(),
        )(super().as_view(**kw))

    def form_valid(self, form: SetPasswordForm) -> HttpResponse:
        form.save()
        messages.success(
            self.request,
            'you have set a password. please log in with it. your username is'
            f' {form.user.get_username()}',
        )
        return super().form_valid(form)


class EmailView(LoginRequiredMixin, BreadcrumbMixin, allauth_views.EmailView):
    breadcrumbs = UpdateProfileView.base_breadcrumbs


class PasswordResetView(allauth_views.PasswordResetView):
    form_class = ResetPasswordForm
