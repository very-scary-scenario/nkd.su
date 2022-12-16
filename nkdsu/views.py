from django.contrib.auth import views as auth_views

from .mixins import MarkdownView


class LoginView(MarkdownView, auth_views.LoginView):
    template_name = auth_views.LoginView.template_name
    title = 'login'
    filename = 'TWITTER.md'
