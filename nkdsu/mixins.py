import codecs
from os import path
from typing import Any

from django.conf import settings
from django.views.generic import TemplateView
from markdown import markdown


class MarkdownView(TemplateView):
    template_name = 'markdown.html'
    filename: str
    title: str

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)

        words = markdown(
            codecs.open(
                path.join(settings.PROJECT_ROOT, self.filename), encoding='utf-8'
            ).read()
        )

        context.update(
            {
                'title': self.title,
                'words': words,
            }
        )

        return context
